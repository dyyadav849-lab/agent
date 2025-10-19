from enum import Enum
from typing import ClassVar, Optional

from llm_evaluation.test_cases_handler import LangsmithEvalTestCase


class LevelZeroTestCase(LangsmithEvalTestCase):
    Plugins: list[dict]
    EvalAgentActions: dict
    EvalStructuredResp: dict
    EvalMustMention: ClassVar[list[str]] = []
    ExpectedOutput: Optional[str] = None


class ZionCategory(Enum):
    QUERY = "Query"
    ISSUE = "Issue"
    APPROVAL_VALIDATE = "Approval/Ask to validate"
    INFORMATIONAL = "Informational"
    OTHERS = "Others"


def _get_universal_search_plugin() -> dict:
    return {"name": "universal_search", "type": "common"}


def _get_gitlab_plugin() -> dict:
    return {"name": "gitlab_job_trace", "type": "common"}


def _get_structured_resp_able_to_answer(category: str) -> dict:
    return {
        "category": category,
        "able_to_answer": True,
    }


def _get_structured_resp_unable_to_answer(category: str) -> dict:
    return {
        "category": category,
        "able_to_answer": False,
    }


def _get_kendra_internal_search_agent_action(expected_call_count: int) -> dict:
    return {
        "universal_search": {
            "tool_name": "universal_search",
            "expected_call_count": expected_call_count,
        }
    }


def _get_kendra_and_gitlab_agent_action(
    kendra_call_count: int,
    gitlab_call_count: int,
) -> dict:
    return {
        "universal_search": {
            "tool_name": "universal_search",
            "expected_call_count": kendra_call_count,
        },
        "gitlab_job_trace": {
            "tool_name": "gitlab_job_trace",
            "expected_call_count": gitlab_call_count,
        },
    }


eval_structure_resp_schema = {
    "category": "str",
    "sources": "list",
    "able_to_answer": "bool",
}


query_source = {"username": "john.doe", "channel_name": "#testing"}

slack_channel_specific_instruction = """You must never ever start reply to user before querying 'universal_search' or 'glean_search', unless you dont have access to internal search tools. You must never use your pretrained knowledge when answering user, unless you have queried search, and the data is not available inside the internal documentation. Even if user is not asking for your help, you must always search internal documentation and be as helpful as possible. You may choose to call other tools that might be useful, but you must always end your process with querying internal documentation before answering user. You can choose to call internal search more than once up to 3 times.

You may choose to skip querying internal search, only IF user's query is a very simple and generic question.

"""


test_case_datas: list[LevelZeroTestCase] = [
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__common_1",
        TestCaseDescription="Common L0 Test 1",
        UserInput="What is Kubernetes?",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        ExpectedOutput="Kubernetes is an open-source platform designed for automating the deployment, scaling, and management of containerized applications. It orchestrates containerized applications to run on a cluster of machines, ensuring efficient resource utilization and high availability. Here are some key components and concepts of Kubernetes:\n1. Cluster: A group of physical or virtual machines (nodes) that run containerized applications.\n2. Pod: The smallest deployable unit in Kubernetes, which can contain one or more containers.\n3. Control Plane: Manages the overall operation of the cluster, including components like the API server, scheduler, and controller manager.\n4. Nodes: Individual machines within a cluster that run and manage containers.\n5. ReplicaSet: Ensures a specified number of pod replicas are running at any given time.\n6. Deployment: Manages the deployment and scaling of ReplicaSets.\n7. Service: Defines a logical set of pods and a policy to access them.",
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__common_2",
        TestCaseDescription="Common L0 Test 2",
        UserInput="Sum of 1+1",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        ExpectedOutput="The sum of 1 + 1 = 2",
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__universal_search",
        TestCaseDescription="Test Universal Search",
        UserInput="What is conveyor?",
        ExpectedOutput="Conveyor is an in-house continuous integration and continuous delivery (CI/CD) solution developed and supported by Grab's Developer Platform team. It is designed to help build, test, monitor, and deploy artifacts and UCM configuration changes in an automated fashion using interactive pipeline models. Conveyor is built using Spinnaker with additional services to support the current continuous integration process at Grab.\nKey features of Conveyor include:\n1. Automated Deployments: Conveyor automates the deployment process from the moment reviews are approved, ensuring that deployments are fully owned by the teams responsible for their services.\n2. Pipeline as Code: Conveyor uses a pipeline-as-code approach, allowing teams to define their deployment pipelines in code.\n3. Rolling Canary Deployments: Conveyor supports rolling canary deployments, which implement a fine-grained progressive rollout mechanism for deployment.\n4. Integration with UCM: Conveyor integrates with UCM to manage configuration changes.\n5. Interactive Pipeline Models: Conveyor provides interactive models to visualize and manage the deployment process.\n6. Emergency Pipelines: Conveyor includes emergency pipelines that can be used during critical situations with on-call lead approval.",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__universal_search_attr_filter",
        TestCaseDescription="Test universal search plugin with attribute filtering",
        UserInput="What is grab-kit?",
        ExpectedOutput="Grab-Kit is a standard framework used at Grab for building Go backend services. It consists of two main components:\n1. Grab-Kit Framework: A Go-based RPC framework designed for creating Go microservices.\n2. Grab-Kit CLI: A command-line tool that complements the framework by generating scaffolding and boilerplate code for services, ensuring consistency and adherence to Grab's standards and best practices.",
        Plugins=[
            {
                "name": "universal_search",
                "type": "common",
                "metadata": {
                    "AttributeFilter": {
                        "OrAllFilters": [
                            {
                                "EqualsTo": {
                                    "Key": "entity_name",
                                    "Value": {"StringValue": "grab-kit"},
                                }
                            }
                        ]
                    }
                },
            }
        ],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__universal_search_3",
        TestCaseDescription="Asking some context not available in the system.",
        UserInput="What does ab4k8s mean?",
        ExpectedOutput="Im sorry, Im unable to find what does 'ab4k8s' mean",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__universal_search_multiple_queries",
        TestCaseDescription="Test performing multiple universal search",
        UserInput="What conveyor and gandalf tools does?",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(2),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_1",
        TestCaseDescription="General Query",
        UserInput="<@WS6RVJ67J> has submitted a form. Details as below :\n\n*Issue Description:* How to find the latest release tag of the service in meks?\n*Service:* Conveyor\n*Request Type:* General Query\n*Urgency:* Non Urgent - Trivial Issue/General Query\n*User search for similar issue on Slack :* Yes\n\n*Other Useful Information:* \n```I found this link in #conveyor, it can only work with services running on EC2. Please advise what is the variable we should use to get the tag for MEKS services \n\n<https://api.conveyor.myteksi.net/asg-tag/version/release?service=thumper&amp;cluster=stg&amp;account=grab-main&amp;region=ap-southeast-1|https://api.conveyor.myteksi.net/asg-tag/version/release?service=thumper&amp;cluster=stg&amp;account=grab-main&amp;region=ap-southeast-1>```\n*Things user already tried to resolve this:* \n``````",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_2",
        TestCaseDescription="Test categorization 2",
        UserInput="<@U01QSDL9HD5> has submitted a form. Details as below :\n\n*Issue Description:* add @mingkit.luk for staging/food-cms and production/food-cms environment\n*Service:* Web-kit Platform\n*Request Type:* Non Production Impacting Issue/Troubleshooting\n*Urgency:* Non Urgent - Trivial Issue/General Query\n*User search for similar issue on Slack :* Yes\n\n*Other Useful Information:* \n```Hi, could I get @mingkit.luk added to the following environments\n\nstaging/food-cms <https://gitlab.myteksi.net/engineering/web-kit/-/environments/14020|https://gitlab.myteksi.net/engineering/web-kit/-/environments/14020>\nproduction/food-cms <https://gitlab.myteksi.net/engineering/web-kit/-/environments/14069|https://gitlab.myteksi.net/engineering/web-kit/-/environments/14069>\n\nAlso, is there a way to self-serve this ourselves? We're also happy to attach the environment to our ldap group @grab-food/delv-sdk-web```\n*Things user already tried to resolve this:* \n``````",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.APPROVAL_VALIDATE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_3",
        TestCaseDescription="Test categorization 3",
        UserInput=":yellow-alert: ANNOUNCEMENT :yellow-alert: @channel We hope this message finds you well! At Concedo, we're always looking for ways to improve your experience. That's why we're reaching out to you - because who better to guide us than the very people we serve? :gift: Your Voice Matters - Make “access denied” a thing of the past! We've all felt the frustration of juggling multiple roles, experiencing access denials at crucial moments, and the looming threat of security and audit breaches. Here's your chance to let us know your biggest pain points :rocket: We Need Your Insights! We've crafted a short survey of no more than 6 questions. Your feedback is invaluable and will directly influence our upcoming projects and enhancements. :point_right: Take the Survey Now! Your input is crucial for us to deliver the exceptional service you deserve. Let's make Concedo even better, together! Thank you for your time and support! Regards,",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.INFORMATIONAL.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_4",
        TestCaseDescription="Test categorization 4",
        UserInput="@yonglian.hii has submitted a form. Details as below :\n\n*Issue Description:* Is there any recommended approach for querying public IPv4 address of our instance?\n*Service:* Others\n*Request Type:* General Query\n*Urgency:* Non Urgent - Trivial Issue/General Query\n*User search for similar issue on Slack :* Yes\n\n*Other Useful Information:* \n``````\n*Things user already tried to resolve this:* \n``````",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_5",
        TestCaseDescription="Test categorization 5",
        UserInput="I am deploying PROD here https://conveyor.myteksi.net/execution/01GVYXYX2MGBZRMZ13KHWAB5Y1",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.INFORMATIONAL.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_6",
        TestCaseDescription="Test categorization 6",
        UserInput="fyi oncall-developer-home, Will deploy these developer web-kit app changes to beta and production today ```### developer (NOTE) Release: (WARNING) Rollback: Changes: | commit | author | description | ----- | ----- | ----- | | Dendi Abdul Rohim | remark",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.INFORMATIONAL.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_7",
        TestCaseDescription="Test categorization 7",
        UserInput="Hello Cosmos team DataDog *APPLIED* a new contract to Grab *in February 2023*, with the following discount • *Custom Metrics:* from `$ 0.50/100 custom metrics` to `$ 0.40/100 custom metrics` • *Infra Host:* from `$ 9.00/host/30 days` to `$ days` MR I",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.INFORMATIONAL.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_8",
        TestCaseDescription="Test categorization 8",
        UserInput="Greetings Grabbers, :announcement: !here We would like to inform you that on Tuesday, March 21st, We will be shifting our Multi Factor Authentication (MFA) tool from DUO to Jumpcloud (JC) for *datadog:* 3 - 4pm SGT, *lightstep:* 4 - 5 pm SGT enterprise",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.INFORMATIONAL.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_9",
        TestCaseDescription="Test categorization 9",
        UserInput="https://jira.grab.com/browse/DELVPS-3459?atlOrigin=eyJpIjoiYjM0MTA4MzUyYTYxNDVkY2IwMzVjOGQ3ZWQ3NzMwM2QiLCJwIjoianN3LWdpdGxhYlNNLWludCJ9|DELVPS-3459 [devHome] update proto in getProjectByID https://gitlab.myteksi.net/gophers/go/-/merge_requests/78842 cc to",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.APPROVAL_VALIDATE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_10",
        TestCaseDescription="Test categorization 10",
        UserInput="Hello [~JIRAUSER94101], can you help to add the permission for me and [~JIRAUSER78024] to approve `/pe/developer-home/mocks/` as well? thanks youu:thankyou:",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.APPROVAL_VALIDATE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_11",
        TestCaseDescription="Test categorization 11",
        UserInput="hi team, can i deploy those change in devhome PROD? oncall-developer-home Flag Changes (only showing the last 20, refer to 'Changes in UCM' for more): ```lang=diff,name=v20230317.0640.53481.devhome/config:app --- a/config/app~prd.toml +++ -kairosELB = =",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.APPROVAL_VALIDATE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_11",
        TestCaseDescription="Test categorization 11",
        UserInput="hi oncall-observability - need help with this PD request for [~JIRAUSER75754] please, it's been approved already by she still doesn't have access. https://permissions.engineering.grab.com/request/23616",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.ISSUE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_12",
        TestCaseDescription="Test categorization 12",
        UserInput="Hi team oncall-observability Please help on this https://jira.grab.com/browse/OBSERVREQ-798?filter=-2|ticket to update my pagerduty permission.",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.APPROVAL_VALIDATE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_13",
        TestCaseDescription="Test categorization 13",
        UserInput="hey oncall-developer-home would that be possible for me to deploy the latest master in STG now and deploy it later to PRD? Saw PRD is on quite an old commit",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.APPROVAL_VALIDATE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_14",
        TestCaseDescription="Test categorization 14",
        UserInput="hey oncall-developer-home https://conveyor.myteksi.net/execution/01GWY1C072HSE5Z3Y86KSSV0GS/01GWY1C094R37636WZRDCT6MCP seems that STG pipeline failed due to high hystrix error, possible to check on it? seems to be related to hystrix triggered on meximum",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.ISSUE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_15",
        TestCaseDescription="Test categorization 15",
        UserInput="Hi Team, could you check why we got this error in *STG* for this rpc call *InternalCreateProject* go/pe/developer-home/internal/z_grabkit/z_api/z_api.go:4416 ```ServerError: target=, reason=internal, msg=an error occurred in the server. please try again =",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.ISSUE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_16",
        TestCaseDescription="Test categorization 16",
        UserInput="Hi team, Irene reported that the editor isnt working for her on this doc. https://helix-staging.stg.nexus.int.engtools.net/catalog/default/component/superset-doc-review/docs/1-dataset/Semantic_Layer This is reproducible for me too for all pages of this to",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.ISSUE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_17",
        TestCaseDescription="Test categorization 17",
        UserInput="Hi team, can i make a feature request/suggestion for the editor? It'll be good to have a preview mode in the editor. If i do not use the toolbar's buttons, such as code block, and just add my markdown manually, I'm not able to see the changes. Having a i",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.INFORMATIONAL.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_18",
        TestCaseDescription="Test categorization 18",
        UserInput="oncall-developer-home Can you plz help lookup who created or who may know `HokBen` in `staging` ? partnerID 846f0816-2980-4f84-8f57-83f603babf20 OAtuh clientID 978e4fe6f1d74852b248631eced5ff23 this partner is trying to obtain access token in Production",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_19",
        TestCaseDescription="Test categorization 19",
        UserInput="Hi team, is this the correct place to request for pagerduty user offboarding? We have an https://grabtaxi.pagerduty.com/users/PENCRTV|individual (ranjan ashish, that has recently exited the company and he has kindly informed us that his PD acc is still to",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.APPROVAL_VALIDATE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_20",
        TestCaseDescription="Test categorization 20",
        UserInput="What is spiderman",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_21",
        TestCaseDescription="Test categorization 21",
        UserInput="What is midgard",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_22",
        TestCaseDescription="Test categorization 22",
        UserInput="What is recursion",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_23",
        TestCaseDescription="Test categorization 23",
        UserInput="What is the meaning of apex in english?",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_24",
        TestCaseDescription="Test categorization 24",
        UserInput="hey oncall-developer-home we detected some clientID leaked in github publicly, would that be possible for us to check the clientID is belongs to any partners in dev portal?",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_26",
        TestCaseDescription="Test categorization 26",
        UserInput="Hi Cosmos team, (for Monday :slightly_smiling_face: ) do you know why we have a huge difference between `Amortized` and `Actual` in Azure for Geo subscriptions? For context we have also RI that I assume are not captured in `actual` of this subscription, a",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_27",
        TestCaseDescription="Test categorization 27",
        UserInput="Hey team, seems local rate limit will only applied for default grpc protocol from the code commons/util/grab-kit/endpoint/quotamiddleware/distributed_rate_limiter.go:77, is it able to limit the traffic in api level (http protocol)? Thanks a lot! :thankyou:",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_28",
        TestCaseDescription="Test categorization 28",
        UserInput="Hello team, can I ask how to solve this issue? I'm migrating docs from wiki to helix https://helix.engtools.net/catalog/default/component/aws-databricks/docs ",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.ISSUE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_29",
        TestCaseDescription="Test categorization 29",
        UserInput="has submitted a form. Details as below : *Issue Description:* Creating CRON Jobs *Service:* Others *Request Type:* General Query *Urgency:* Non Urgent - Trivial Issue/General Query *User search for similar issue on Slack :* Yes *Other Useful Information:* ```Hi team, wanted to ask if there's any documentation regarding creating cron jobs for regularly scheduled jobs for a service? Something like creating a job that calls a service's endpoint at a certain time daily Thank you!``` *Things user already tried to resolve this:*",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_30",
        TestCaseDescription="Test categorization 30",
        UserInput="who channel should I ask regarding managed-eks",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_31",
        TestCaseDescription="Test categorization 31",
        UserInput="I am a new joiner in Grab, what are the things I should know",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_33",
        TestCaseDescription="Test categorization 33",
        UserInput="what is GTM",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_35",
        TestCaseDescription="Test categorization 35",
        UserInput="Hi How to connect to read Hudi table in data lake via PowerBI?",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_36",
        TestCaseDescription="Test categorization 36",
        UserInput="Hi team @oncall-caspian-volga @kaiyiu.leung, ovo_raw.ovo_chronicler_publish_transaction_history failed on 22nd August. Could you please check?",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.ISSUE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_37",
        TestCaseDescription="Test categorization 37",
        UserInput="Hi team, is there a way I can delete an existing schema created via QuickSilver?",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.ISSUE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_39",
        TestCaseDescription="Test categorization 39",
        UserInput="[~JIRAUSER94101] please help review devhome ucm prd changes https://helix.engtools.net/ucm?repo=devhome&amp;config_key=config:FEConfigs&amp;group=grabtaxi&amp;tab=Pending%20Approval",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.APPROVAL_VALIDATE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_40",
        TestCaseDescription="Test categorization 40",
        UserInput="oncall-developer-home question for `OAuth2 Clients`. For production and staging, will the Client ID be the same or different? or will this be dependent on our partner's set-up.",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_41",
        TestCaseDescription="Test categorization 41",
        UserInput="Hi oncall-developer-home, question for https://developer-admin.grab.com/projects/faa4ae96-67e5-446c-8625-6f5a7d895f8f This is currently being used for `GrabFood Point of Sale API`. Was wondering if we can use the same Partner Project for `GrabExpress",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_42",
        TestCaseDescription="Test categorization 42",
        UserInput="hi oncall-developer-home please help to review thankss! UCM: https://helix.engtools.net/ucm?repo=devhome&amp;config_key=config:features&amp;group=grabtaxi&amp;tab=Pending%20Approval",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.APPROVAL_VALIDATE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_43",
        TestCaseDescription="Test categorization 43",
        UserInput="hey oncall-developer-home would that be possible for me to deploy the latest master in STG now and deploy it later to PRD? Saw PRD is on quite an old commit",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.APPROVAL_VALIDATE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_45",
        TestCaseDescription="Test categorization 45",
        UserInput="Hi oncall-developer-home when creating OAuth client on developer home portal, the `sso expiry` maximum duration is set to 72h, this is no longer true with the introduction of `remember me` can we • update the maximum duration to &lt;=90d • make the",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_46",
        TestCaseDescription="Test categorization 46",
        UserInput="oncall-developer-home plz help review `devhome-beta` UCM and publish https://helix.engtools.net/ucm?repo=devhome-beta&amp;config_key=config:FEConfigs&amp;group=grabtaxi&amp;tab=Pending%20Approval thank you :pray:",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.APPROVAL_VALIDATE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_47",
        TestCaseDescription="Test categorization 47",
        UserInput="fyi oncall-developer-home, Will deploy these developer web-kit app changes to beta and production today ```### developer (NOTE) Release: (WARNING) Rollback: Changes: | commit | author | description | ----- | ----- | ----- | | Dendi Abdul Rohim | remark",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.INFORMATIONAL.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_48",
        TestCaseDescription="Test categorization 48",
        UserInput="fyi oncall-developer-home, i'm deploying latest master to stg :pray:",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.INFORMATIONAL.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_49",
        TestCaseDescription="Test categorization 49",
        UserInput="deployment is done",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.INFORMATIONAL.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_50",
        TestCaseDescription="Test categorization 50",
        UserInput="Hi oncall-developer-home Can you help check this error?",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.ISSUE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_51",
        TestCaseDescription="Test categorization 51",
        UserInput="hioncall-developer-home could you help to take a look at project with `projectUUID=a50fe03e-fcc8-48b5-8145-285f1a3e692d` , we can not fetch merchant that links to project. see 1 error with code 405. ```external.user_service : Failed to fetch merchants,",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.ISSUE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_52",
        TestCaseDescription="Test categorization 52",
        UserInput="Hi team oncall-developer-home, may I know how to got access to the `[Debug] Devhome Debug Projects`?",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_53",
        TestCaseDescription="Test categorization 53",
        UserInput="eloo oncall-developer-home at the moment we have big padding / unused space left and right. we want stretch this to utilize empty space making the project navigation is on the left. can we allow to do that?",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_54",
        TestCaseDescription="Test categorization 54",
        UserInput="&gt; https://gitlab.myteksi.net/ucm/prod-grabtaxi-group/devhome/devhome/-/merge_requests/1 oncall-developer-home hi can help review approve, for stg ucm",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.APPROVAL_VALIDATE.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__categorization_55",
        TestCaseDescription="Test categorization 55",
        UserInput="@hofid.mashudi has submitted a form. Details as below  Tool/Service: Conveyor\nType: Issue\nUrgency: Urgent - Impacting Production\nSummary/Description:\nHi team, we noticed an issue on MEKS and want to rollback food-order-batching service from to EC2, last time we decommissioned the EC2 by setting up min and max = 0, and the question is how we can have the same version tags on the EC2? as the service is stream consumer based we can't spin up the current tags in the EC2 ASG.\nIs there any way to update the ASG to have the same tags as the MEKS deployment?\nThings user already tried to resolve this:",
        Plugins=[_get_universal_search_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_internal_search_agent_action(1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__gitlab_1",
        TestCaseDescription="Test gitlab job pipeline 1",
        UserInput="Type: Issue\nInfra Org: GT\nMEKS Category: Deployment Issue\nUrgency: Not Urgent\nChecked FAQ/Slack for similar issues: Yes\nIssue Summary / Further Details:\nIm unable to deploy my `einherjar` service to production. Im unsure what is the root issue.\nGitlab log: https://gitlab.myteksi.net/techops-automation/service-deployment/einherjar/-/jobs/72079586\nThings user already tried to resolve this:\n- Tried to install controllers to production\n- Tried to Rollback production to latest succesful",
        Plugins=[_get_universal_search_plugin(), _get_gitlab_plugin()],
        EvalStructuredResp=_get_structured_resp_able_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_and_gitlab_agent_action(1, 1),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__test_no_search_system_1",
        TestCaseDescription="Test No Search System 1",
        UserInput="Type: Issue\nInfra Org: GT\nMEKS Category: Deployment Issue\nUrgency: Not Urgent\nChecked FAQ/Slack for similar issues: Yes\nIssue Summary / Further Details:\nIm unable to deploy my `einherjar` service to production. Im unsure what is the root issue.\nGitlab log: https://gitlab.myteksi.net/techops-automation/service-deployment/einherjar/-/jobs/72079586\nThings user already tried to resolve this:\n- Tried to install controllers to production\n- Tried to Rollback production to latest succesful",
        Plugins=[],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_and_gitlab_agent_action(0, 0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__test_no_search_system_2",
        TestCaseDescription="Test No Search System 2",
        UserInput="hey oncall-developer-home we detected some clientID leaked in github publicly, would that be possible for us to check the clientID is belongs to any partners in dev portal?",
        Plugins=[],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_and_gitlab_agent_action(0, 0),
    ),
    LevelZeroTestCase(
        TestCaseName="ti_bot_level_zero__test_no_search_system_3",
        TestCaseDescription="Test No Search System 3",
        UserInput="who channel should I ask regarding managed-eks",
        Plugins=[],
        EvalStructuredResp=_get_structured_resp_unable_to_answer(
            ZionCategory.QUERY.value
        ),
        EvalAgentActions=_get_kendra_and_gitlab_agent_action(0, 0),
    ),
]
