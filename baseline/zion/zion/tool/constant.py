general_search_tool_desc = """Used to search internal documentations regarding code, engineering, server services, products, learning, bulletin or other general internal documentation inside Grab.

To decide whether to use this tool, you must always look through the user's first query very carefully. You must always use this tool before answering user, if the user's FIRST query:
1. contains any keywords related to technical questions or software engineering related questions such as errors, issues or questions.
2. is asking on person, oncall, slack channel or team to contact.
3. Contains keyword like sso, client, portal, conveyor, error, auth, git, database, ci pipeline, hystrix, script, logging, environment issue, documentation (staging or production)
4. contains a fictional character name or location, it's safe to assume it's an internal service/tool
5. has acronyms"""

mr_creation_search_tool_desc = """
The search tool is designed to retrieve and summarize information from URLs provided by the user. It excludes URLs related to merge requests and Git repositories, focusing instead on extracting relevant content, metadata, or document data from other types of URLs. The tool helps to provide concise summaries of the content in linked documents for easier understanding and further processing.
"""

hades_kb_endpoint = "/slack/chathistory/knowledgebase"

# Kibana Tool
# Common
TRUNCATED_TAG = "...[TRUNCATED]"
MAX_LEN_LOG = 700
MAX_ADDITIONAL_DATA_LEN_MSG = 1000
MAX_STACKTRACE_LEN_MSG = 2000

# Delimiter
LINE_BREAK_DELIMITER = "\n"
MAX_KIBANA_LEN_MSG = 2900
KIBANA_SINGLE_DOC_URL_FORMAT = "%s#/doc/%s/%s?id=%s"
MAX_REQUEST_ID_SAMPLE = 3
OPENSEARCH_TO_KIBANA_URL = {
    "opensearch-dashboards.obs.stg-myteksi.com": "https://kibana.stg-myteksi.com/app/discoverLegacy",
    "opensearch-dashboards.obs.myteksi.net": "https://kibana.myteksi.net/app/discoverLegacy",
}
