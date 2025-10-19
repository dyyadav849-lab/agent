import toml
from datadog import initialize
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from starlette.middleware.sessions import SessionMiddleware

from app.auth.modes import SessionAuthMode, get_session_auth_mode
from app.core.config import app_config, logger
from app.routes.api import router
from app.tracing.tracer import trace_provider


def get_app() -> FastAPI:
    project_metadata = toml.load("pyproject.toml")["tool"]["poetry"]
    app = FastAPI(
        title=project_metadata["name"],
        version=project_metadata["version"],
        description=project_metadata["description"],
    )
    app.include_router(router)

    if get_session_auth_mode(app_config.auth_mode) != SessionAuthMode.PROXY:
        app.add_middleware(
            SessionMiddleware, secret_key=app_config.session_secret_key, https_only=True
        )

    return app


app = get_app()

# check to not start fast api instrumentor at local environment
if app_config.environment != "dev":
    # enables for automatic tracing over endpoints' start-end
    # for fined-grained tracing, manual tracing will be required
    instrumentor = FastAPIInstrumentor()
    instrumentor.instrument_app(
        app=app,
        tracer_provider=trace_provider,
        excluded_urls=app_config.otel_excluded_endpoints,
    )

    # init statsd client
    initialize(
        statsd_socket_path=app_config.dd_statsd_socket_path,
    )
    logger.info(
        f"Initialized statsd socket to client {app_config.dd_statsd_socket_path}"
    )
