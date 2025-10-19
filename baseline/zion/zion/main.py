from __future__ import annotations

from typing import Annotated

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from zion.config import global_config, is_langsmith_enabled, logger  # isort:skip, Always initialize environment variables first.

import json
import time
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import ddtrace
import jwt
from datadog import initialize
from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from langserve import add_routes
from langsmith import Client as LangSmithClient
from llm_evaluation.evaluators import (
    EXPECTED_OUTPUT_KEY,
    llm_as_judge_evaluator,
)
from llm_evaluation.test_cases_handler import EvaluateLLMAgent
from llm_kit.middleware import DatadogMetricMiddleware
from llm_kit.util.otel.instrumentor import OTELInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from pydantic.main import BaseModel

from zion.agent.zion_agent import (
    ZionAgent,
)
from zion.credentials.google import (
    init_google_credentials,
)
from zion.data.agent_plugin.constant import (
    AGENT_HTTP_PLUGIN_TYPE,
    AGENT_OPENAPI_PLUGIN_TYPE,
)
from zion.data.agent_plugin.data import (
    AgentPlugin,
    QueryAgentPluginRequest,
)
from zion.data.agent_plugin.database_handler import (
    create_agent_plugin,
    duplicate_agent_plugin_checking,
    get_agent_plugin_database,
    get_all_agent_plugins_database,
    get_specific_agent_plugins_database,
    set_plugin_to_is_moved,
    update_agent_plugin,
)
from zion.data.agent_plugin.util import get_agent_plugin_json
from zion.evaluations.custom_evaluator import (
    able_to_answer_user_evaluator,
    agent_actions_evaluator,
    must_mention_evaluator,
    should_trigger_mttx_evaluator,
    structured_response_type_evaluator,
    structured_response_value_evaluator,
    user_query_category_evaluator,
)
from zion.evaluations.level_zero_test_cases import (
    eval_structure_resp_schema,
    query_source,
    slack_channel_specific_instruction,
    test_case_datas,
)
from zion.jobs.job_runner import job_runner
from zion.openapi.openapi_plugin import OpenAPIPlugin
from zion.openapi.util import (
    check_http_plugin_data,
    check_supported_openapi_url,
    check_valid_openapi_version,
)
from zion.util import helix
from zion.util.gitlab import load_gitlab_file_in_dict
from zion.util.secure_endpoint import check_agent_secret
from zion.util.service_mesh import get_service_mesh

ddtrace.patch(fastapi=True)
app = FastAPI(
    title="Zion",
    version="1.0",
    description="Home of the LLM Agents",
)

origins = [
    "https://ti-bot-configuration.grab.dev",
    "https://ti-bot-configuration.stg-myteksi.com",
    "https://ti-bot-configuration.grab.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(DatadogMetricMiddleware)


class HelloResponse(BaseModel):
    message: str


class AgentLangsmithEvalResponse(BaseModel):
    message: str
    test_project_name: str
    test_run_name: str


class PluginModifyRequestResponse(BaseModel):
    message: str


class ValidateSwaggerResponse(BaseModel):
    message: str
    swagger_data: str


class SwaggerPath(BaseModel):
    url: str


@app.middleware("http")
async def decode_token(request: Request, call_next: Callable[[Request]]) -> Response:
    def raise_invalid_token_error() -> None:
        err = "Invalid Token"
        raise jwt.InvalidTokenError(err)

    token = request.headers.get("authorization")
    if token:
        try:
            _, payload, _ = token.split(".")
            decoded_token_payload = jwt.utils.base64url_decode(payload)
            json_token_payload = decoded_token_payload.decode("utf-8")
            token_payload = json.loads(json_token_payload)
            email = token_payload.get("email")
            request.state.email = email
            if not email:
                raise_invalid_token_error()
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                content={"error": "Token expired. Please log in again."},
                status_code=401,
            )
        except (jwt.InvalidTokenError, Exception):
            return JSONResponse(
                content={"error": "Invalid token. Please log in again."},
                status_code=401,
            )
    return await call_next(request)


# This is used for heartbeats and health checks, do not remove
@app.get("/", response_model=HelloResponse, summary="Greetings")
async def hello(greeting: str = "Hello", name: str = "World") -> dict[str, Any]:
    """Returns greeting message."""
    message = f"{greeting} {name}!"
    return {"message": message}


@app.get(
    "/agent-plugin/{agent_name}",  # noqa: FAST003
    response_model=list[dict[str, Any]],
    summary="Gets agent plugin based on agent_name, username and channel_name",
)
async def get_agent_plugin(
    request: Request,
    slack_channels: str = Query(  # noqa: FAST002
        "", description="Filter by Slack channel name. Must be start with #"
    ),
    users: str = Query("", description="Filter by Slack username"),  # noqa: FAST002
    plugin_keyword: str = Query(  # noqa: FAST002
        "",
        description="Search plugin with keyword, by `name_for_model` and `name_for_human`",
    ),
) -> list[AgentPlugin]:
    """Get a list of agent plugin based on agent_name, username and channel_name"""
    _, _, agent_name = request.url.path.split("/")

    try:
        check_agent_secret(request, agent_name)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Agent secret invalid: {e}") from e

    db_agent_plugins = get_agent_plugin_database(
        QueryAgentPluginRequest(
            agent_name=agent_name,
            channel_name=slack_channels,
            username=users,
            plugin_keyword=plugin_keyword,
        )
    )

    if db_agent_plugins is None:
        # early return if no agent plugin found
        return [{}]

    return get_agent_plugin_json(db_agent_plugins, open_api=False)


@app.get(
    "/run_job/{job_name}",
    response_model=Any,
    summary="Runs a job based on the job name",
)
async def run_job(
    request: Request,  # noqa: ARG001
    job_name: str,
) -> list[dict[str, str]]:
    """Get a list of agent plugin based on agent_name, username and channel_name"""
    try:
        await job_runner(job_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {"message": f"Job {job_name} has been run successfully"}


@app.get(
    "/plugin-list",
    response_model=list[dict[str, Any]],
    summary="Gets a list of plugins",
)
async def get_agent_plugins(
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    name_for_human: Optional[str] = None,
) -> list[AgentPlugin]:
    """Get a list of all plugins onboarded"""

    db_agent_plugins = get_all_agent_plugins_database(page, page_size, name_for_human)

    return get_agent_plugin_json(db_agent_plugins, open_api=False)


@app.get(
    "/plugin-list/{name_for_model}",
    response_model=list[dict[str, Any]],
    summary="Gets plugin by name_for_model",
)
async def get_agent_plugin_by_name_for_model(
    request: Request,  # noqa: ARG001
    name_for_model: str,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> list[AgentPlugin]:
    """Get a plugin based on name_for_model"""
    db_agent_plugins = get_specific_agent_plugins_database(
        name_for_model, page, page_size
    )

    return get_agent_plugin_json(db_agent_plugins, open_api=False)


@app.post(
    "/agent/{agent_name}/langsmith-eval/{test_project_name}",
    response_model=AgentLangsmithEvalResponse,
    summary="Evaluate the agent's test cases based on the test project name",
)
async def eval_api_handler(
    request: Request,  # noqa: ARG001
    agent_name: str,
    test_project_name: str,
) -> dict[str, str]:
    agent_profile = global_config.agent_profiles.get(agent_name, "")
    agent_executor = ZionAgent()
    agent_executor.agent_profile = agent_profile

    try:
        test_output = EvaluateLLMAgent(
            environment=global_config.environment,
            test_project_name=test_project_name,
            test_project_description=f"Test cases for {agent_name}",
            evaluators=[
                must_mention_evaluator,
                structured_response_type_evaluator,
                user_query_category_evaluator,
                able_to_answer_user_evaluator,
                should_trigger_mttx_evaluator,
                structured_response_value_evaluator,
                agent_actions_evaluator,
                llm_as_judge_evaluator(
                    api_key=global_config.openai_api_key,
                    grabgpt_env=global_config.environment,
                ),
            ],
            test_case_input=lambda test_case_data: {
                "input": getattr(test_case_data, "UserInput", ""),
                "system_prompt_hub_commit": "cauldronbot-qa/dev-ti-bot-level-zero",
                "structured_response_schema_hub_commit": "cauldronbot-qa/dev-ti-bot-level-zero-structured-response",
                "system_prompt_variables": {
                    "slack_channel_specific_instruction": slack_channel_specific_instruction
                },
                "chat_history": [],
                "agent_config": {"plugins": getattr(test_case_data, "Plugins", [])},
                "query_source": query_source,
            },
            test_case_output=lambda test_case_data: {
                EXPECTED_OUTPUT_KEY: getattr(test_case_data, "ExpectedOutput", ""),
                "eval_structured_response_value": getattr(
                    test_case_data, "EvalStructuredResp", ""
                ),
                "eval_agent_actions": getattr(test_case_data, "EvalAgentActions", ""),
                "eval_structured_response_type": eval_structure_resp_schema,
                "eval_must_mention": getattr(test_case_data, "EvalMustMention", ""),
            },
            agent=agent_executor.invoke,
            test_case_datas=test_case_datas,
            langsmith_client=LangSmithClient(
                api_key=global_config.langchain_api_key,
                api_url=global_config.langchain_endpoint,
            ),
        ).evaluate()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except (
        Exception  # , because we want to log the unexpected exceptions
    ) as e:
        logger.error(f"Error occurred while running the test project: {e!s}")
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {
        "message": "Test completed",
        "test_project_name": test_project_name,
        "test_run_name": test_output.experiment_name,
    }


async def agent_request_modifier(config: dict, request: Request) -> dict:
    """Pre-request config modifier for the LangServe agent endpoints"""

    # Parse the agent_name from URL manually as this route parameter is not returning by per_req_config_modifier
    agent_name = request.url.path.split("/")[2]
    json_data: Any = await request.json()
    input_dict = json_data["input"]

    try:
        config["agent_profile"] = check_agent_secret(request, agent_name)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Agent secret invalid: {e}") from e

    # testing the value remapping
    if "input_alt" in input_dict:
        input_dict["input"] = input_dict["input_alt"]
        config["input"] = input_dict

    # pass the config to the runnable function
    return config


@app.post(
    "/agent/{agent_name}/langsmith-eval-dataset/{test_project_name}",
    response_model=None,
    summary="Streaming evaluation of agent's test cases from LangSmith dataset (supports both live agent execution and existing outputs evaluation)",
)
async def eval_dataset_handler(
    request: Request,  # noqa: ARG001
    agent_name: str,
    test_project_name: str,
    agent_input: Optional[dict] = None, # should be convertible to a ZionAgentInput
    use_existing_outputs: bool = Query(  # noqa: FBT001, FAST002
        False,  # noqa: FBT003
        description="Use existing outputs from dataset instead of running agent",
    ),
) -> StreamingResponse:
    """Streaming endpoint for evaluating agent test cases with real-time progress updates.

    Supports two modes:
    - use_existing_outputs=False (default): Runs the agent to generate new outputs for evaluation
    - use_existing_outputs=True: Evaluates pre-existing outputs stored in the dataset
    """
    logger.info(
        "Starting streaming evaluation for agent: %s, project: %s, use_existing_outputs: %s",
        agent_name,
        test_project_name,
        use_existing_outputs,
    )

    from zion.evaluations.langsmith_evaluation import run_langsmith_evaluation_core

    def run_evaluation() -> str:
        try:
            logger.info(
                "Starting evaluation in thread for agent: %s, project: %s",
                agent_name,
                test_project_name,
            )

            # Use the core evaluation function
            import asyncio

            # Run the async core function
            result = asyncio.run(
                run_langsmith_evaluation_core(
                    agent_name=agent_name,
                    test_project_name=test_project_name,
                    agent_input=agent_input,
                    use_existing_outputs=use_existing_outputs,
                )
            )

            logger.info(
                "Evaluation completed successfully for agent: %s, project: %s",
                agent_name,
                test_project_name,
            )

            return json.dumps(
                {
                    "status": result.status,
                    "message": result.message,
                    "test_project_name": result.test_project_name,
                    "test_run_name": result.test_run_name,
                    "results": result.results,
                    "error": result.error,
                }
            )

        except Exception as e:  # noqa: BLE001
            logger.exception(
                "Error in evaluation for agent: %s, project: %s: %s",
                agent_name,
                test_project_name,
                str(e),
            )
            return json.dumps({"status": "error", "message": str(e)})

    def generate_streaming_response() -> Generator[str, None, None]:
        logger.info(
            "Starting streaming response generation for agent: %s, project: %s",
            agent_name,
            test_project_name,
        )
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(run_evaluation)

        # Set a timeout for the evaluation (30 minutes)
        timeout_seconds = 1800
        start_time = time.time()

        try:
            while not future.done():
                # Check for timeout
                if time.time() - start_time > timeout_seconds:
                    logger.error("Evaluation timeout after %d seconds", timeout_seconds)
                    executor.shutdown(wait=False)
                    yield json.dumps(
                        {
                            "status": "error",
                            "message": f"Evaluation timeout after {timeout_seconds} seconds",
                            "test_project_name": test_project_name,
                        }
                    )
                    return

                time.sleep(5 if use_existing_outputs else 10)
                progress_message = (
                    "Running evaluation with existing outputs..."
                    if use_existing_outputs
                    else "Running evaluation..."
                )
                progress_str = json.dumps(
                    {
                        "status": "processing",
                        "message": progress_message,
                        "test_project_name": test_project_name,
                    }
                )
                yield f"{progress_str}\n"

            # Get the result with timeout
            logger.info("Evaluation completed, getting result...")
            result = future.result(timeout=10)  # 10 second timeout for getting result
            logger.info(
                "Streaming response completed for agent: %s, project: %s",
                agent_name,
                test_project_name,
            )
            yield result

        except (TimeoutError, RuntimeError, OSError) as e:
            logger.exception("Error in streaming response generation: %s", str(e))
            yield json.dumps(
                {
                    "status": "error",
                    "message": f"Streaming error: {e!s}",
                    "test_project_name": test_project_name,
                }
            )
        finally:
            executor.shutdown(wait=False)

    return StreamingResponse(
        generate_streaming_response(), media_type="application/x-ndjson"
    )


# Create dynamic agent API endpoints, the following endpoints will be created by LangServe:
# /agent/{agent_name}/invoke
# /agent/{agent_name}/stream
# /agent/{agent_name}/batch
# /agent/{agent_name}/playground
# /agent/{agent_name}/feedback
enable_feedback_endpoint = False
if is_langsmith_enabled():
    enable_feedback_endpoint = True
add_routes(
    app=app,
    path="/agent/{agent_name}",
    runnable=ZionAgent(),
    per_req_config_modifier=agent_request_modifier,
    enable_feedback_endpoint=enable_feedback_endpoint,
)

init_google_credentials()

if global_config.otel_exporter_otlp_endpoint:
    exporter = OTLPSpanExporter(endpoint=global_config.otel_exporter_otlp_endpoint)
    instrumentor = OTELInstrumentor(
        exporter=exporter,
        excluded_urls=global_config.otel_excluded_endpoints.split(","),
        app_name="dev-zion"
        if global_config.environment == "dev"
        else None,  # prd/stg should have app_name set in the environment
    )
    instrumentor.instrument_app(app=app, request=True)

# init statsd client
initialize(
    statsd_socket_path=global_config.dd_statsd_socket_path,
)
logger.info(
    f"Initialized statsd socket to client {global_config.dd_statsd_socket_path}"
)


"""This is only used for local development launch.json testing"""
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)


@app.post(
    "/plugin/request",
    response_model=PluginModifyRequestResponse,
    summary="Create/ Update request for plugin",
)
async def plugin_request(
    plugin_info: dict, mode: Optional[str] = None
) -> dict[str, str]:
    try:
        plugin_info_model = OpenAPIPlugin(**plugin_info)

        if (
            plugin_info_model.api.ref != ""
            and plugin_info_model.type == AGENT_OPENAPI_PLUGIN_TYPE
        ):
            check_supported_openapi_url(plugin_info_model.api.ref)

        if (
            plugin_info_model.api.ref != ""
            and plugin_info_model.type == AGENT_HTTP_PLUGIN_TYPE
        ):
            check_http_plugin_data(plugin_info_model)

        if mode == "create":
            duplicate_agent_plugin_checking(plugin_info_model.name_for_model)
            create_agent_plugin(plugin_info_model)
        elif mode == "update":
            update_agent_plugin(plugin_info_model)
        else:
            set_plugin_to_is_moved(plugin_info_model)

    except ValueError as valueErr:
        raise HTTPException(status_code=409, detail=str(valueErr)) from valueErr
    except KeyError as keyErr:
        raise HTTPException(status_code=404, detail=str(keyErr)) from keyErr
    except Exception as e:
        raise HTTPException(400, "Request body was invalid") from e

    return {"message": "Success"}


@app.post(
    "/validate-swagger-path",
    response_model=ValidateSwaggerResponse,
    summary="Validate swagger path and gets swagger data",
)
async def validate_and_get_swagger(swagger_path: SwaggerPath) -> dict[str, str]:
    """Validate swagger path and gets swagger data onboarded"""

    try:
        openapi_data = load_gitlab_file_in_dict(swagger_path.url)
    ## Catch exception raise from load_gitlab_file_in_dict
    except ValueError as valueErr:
        raise HTTPException(status_code=400, detail=str(valueErr)) from valueErr
    ## Catch file not exists in Gitlab
    except Exception as e:
        raise HTTPException(status_code=404, detail="File Not Found") from e

    try:
        check_valid_openapi_version(openapi_data)
    except (ValueError, NotImplementedError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=400, detail="Failed to identify correct OpenAPI version"
        ) from e

    return {"message": "Success", "swagger_data": json.dumps(openapi_data["paths"])}


@app.get(
    "/token/concedo_helix_token",
    response_model=dict[str, str],
    summary="Gets helix and concedo token",
)
async def get_helix_and_concedo_token() -> dict[str, str]:
    """Get a helix and concedo token"""
    concedo_token, helix_token = helix.get_helix_token()

    return {"concedo_token": concedo_token, "helix_token": helix_token}


@app.get("/test/_get-dependency-graph")
def get_dependency_graph(
    service_name: str,
    env: str = "prd",
) -> JSONResponse:
    return get_service_mesh(service_name, env)


@app.post(
    "/data-collection-pipeline",
    response_model=dict[str, str],
    summary="Run the data collection pipeline to prepare evaluation datasets",
)
async def run_data_collection_pipeline_endpoint(
    dataset_name: Optional[str] = None,
) -> dict[str, str]:
    """Run the data collection pipeline to collect and upload evaluation data to LangSmith"""
    try:
        from zion.evaluations.data_collection.pipeline import run_data_collection

        await run_data_collection(dataset_name=dataset_name)

        final_dataset_name = (
            dataset_name
            or f"auto_evals_data_{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        )

        return {  # noqa: TRY300
            "status": "success",
            "message": "Data collection pipeline completed successfully - evaluation dataset created",
            "dataset_name": final_dataset_name,
        }

    except RuntimeError as e:
        # Case when no data was collected
        error_message = str(e)
        if "No data points collected" in error_message:
            return {
                "status": "warning",
                "message": "Data collection pipeline completed but no data was collected. This may be due to service unavailability or no matching data in the specified time period",
                "dataset_name": dataset_name
                or f"auto_evals_data_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
                "error": error_message,
            }
        raise

    except Exception as e:
        logger.exception("Data collection pipeline failed")
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e!s}") from e


class TestGrabGPTAPIKeyValid(BaseModel):
    type: str
    model_name: str


@app.post("/test/grabgpt-api-key-valid")
def test_grabgpt_api_key_valid(
    test_grabgpt_api_key_valid: TestGrabGPTAPIKeyValid,
    custom_api_key: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    if custom_api_key is None:
        raise HTTPException(
            status_code=400, detail="no custom_api_key provided in header"
        )
    endpoint_to_use = global_config.openai_endpoint
    if test_grabgpt_api_key_valid.type == "private":
        endpoint_to_use = global_config.private_openai_endpoint
    base_url = f"{endpoint_to_use}/unified/v1/"
    model = ChatOpenAI(
        model=test_grabgpt_api_key_valid.model_name,
        openai_api_key=custom_api_key,
        openai_api_base=base_url,
    )

    try:
        response = model.invoke([HumanMessage(content="What is 1 + 1")])

    except Exception as e:  # noqa: BLE001
        return {"Exception": f"Unable to call unified endpoint with error: {e}"}
    return {"data": response}
