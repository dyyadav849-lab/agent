# ruff: noqa: SLF001, because it's a test file

from unittest.mock import MagicMock, patch


def test_search_with_jql() -> None:
    mock_jira = MagicMock()
    mock_jira.jql.return_value = {"issues": []}

    with patch("zion.tool.jira_jql_search_tool.Jira", return_value=mock_jira):
        from zion.tool.jira_jql_search_tool import JiraJQLSearch, JiraJQLSearchInput

        input_data = JiraJQLSearchInput(jql="project = Test", start=0, limit=10)
        jira_search = JiraJQLSearch()

        results = jira_search._search_with_jql(
            input_data.jql, input_data.start, input_data.limit
        )

        # Assert the results
        assert "issues" in results
        assert isinstance(results, str)


def test_reduce_jql_results() -> None:
    mock_jira = MagicMock()
    mock_jira.jql.return_value = {
        "issues": [
            {
                "self": "url",
                "expand": "yes",
                "fields": {
                    "reporter": {"name": "Test Reporter", "displayName": "Test"},
                    "assignee": {"name": "Test Assignee", "displayName": "Test"},
                    "components": [{"name": "Test"}],
                    "status": {"name": "Test Status"},
                },
            }
        ]
    }

    with patch("zion.tool.jira_jql_search_tool.Jira", return_value=mock_jira):
        from zion.tool.jira_jql_search_tool import JiraJQLSearch

        jira_search = JiraJQLSearch()
        output = jira_search._reduce_jql_results(mock_jira.jql.return_value)

        assert "issues" in output

        for issue in output["issues"]:
            assert "self" not in issue
            assert "expand" not in issue
            assert "fields" in issue
            assert "displayName" in issue["fields"]["reporter"]
            assert "displayName" in issue["fields"]["assignee"]
            assert "name" in issue["fields"]["status"]
            assert "components" in issue["fields"]
            for component in issue["fields"]["components"]:
                assert "name" in component
