import json
from unittest.mock import MagicMock, patch

import pytest

from zion.util.gitlab import (
    get_gitlab_repo_name,
    gitlab_blob_url_error,
    gitlab_job_url_error,
    is_gitlab_blob_url,
    parse_gitlab_job_url,
    parse_gitlab_url,
)


def test_is_gitlab_blob_url() -> None:
    # Test with valid GitLab blob URL
    assert (
        is_gitlab_blob_url("https://gitlab.com/myproject/-/blob/master/file.py")
        is False
    )

    assert (
        is_gitlab_blob_url("https://gitlab.myteksi.net/myproject/-/blob/master/file.py")
        is True
    )

    # Test with no blob in url
    assert (
        is_gitlab_blob_url("https://gitlab.com/myproject/-/files/master/file.py")
        is False
    )

    assert (
        is_gitlab_blob_url(
            "https://gitlab.myteksi.net/myproject/-/files/master/file.py"
        )
        is False
    )

    # Test with empty string
    assert is_gitlab_blob_url("") is False


def test_parse_gitlab_url() -> None:
    # Test with valid GitLab URL
    url = "https://gitlab.com/myproject/-/blob/master/file.py"
    project_handle, branch_name, file_path = parse_gitlab_url(url)
    assert project_handle == "myproject"
    assert branch_name == "master"
    assert file_path == "file.py"

    url = "https://gitlab.myteksi.net/myproject/-/blob/develop/folder/file.py"
    project_handle, branch_name, file_path = parse_gitlab_url(url)
    assert project_handle == "myproject"
    assert branch_name == "develop"
    assert file_path == "folder/file.py"

    # Test with invalid GitLab URL
    url = "https://gitlab.com/myproject/-/blob/master"
    with pytest.raises(ValueError, match=str(gitlab_blob_url_error)):
        parse_gitlab_url(url)

    url = "https://gitlab.myteksi.net/myproject/-/blob/develop/"
    with pytest.raises(ValueError, match=str(gitlab_blob_url_error)):
        parse_gitlab_url(url)


def test_parse_gitlab_job_url() -> None:
    # Test with valid GitLab job URL
    url = "https://gitlab.myteksi.net/myproject/-/jobs/12345"
    project_name, job_id = parse_gitlab_job_url(url)
    assert project_name == "myproject"
    assert job_id == "12345"

    url = "https://gitlab.myteksi.net/myproject/subproject/-/jobs/67890"
    project_name, job_id = parse_gitlab_job_url(url)
    assert project_name == "myproject/subproject"
    assert job_id == "67890"

    # Test with invalid GitLab job URL
    url = "https://gitlab.com/myproject/-/jobs/"
    with pytest.raises(ValueError, match=str(gitlab_job_url_error)):
        parse_gitlab_job_url(url)

    url = "https://gitlab.myteksi.net/myproject/-/jobs/abc"
    with pytest.raises(ValueError, match=str(gitlab_job_url_error)):
        parse_gitlab_job_url(url)


def test_load_remote_openapi_file() -> None:
    fake_file_content = {
        "file_name": "fake_file_name",
        "file_content": "fake_file_content",
    }
    test_cases = [
        {
            "blob_url": "https://gitlab.myteksi.net/test-group/test-project/-/blob/master/testsdk/testpb/test.swagger.yml",
            "expected_result": fake_file_content,
        },
        {
            "blob_url": "https://gitlab.myteksi.net/test-group/test-project/-/blob/master/testsdk/testpb/test.swagger.yaml",
            "expected_result": fake_file_content,
        },
        {
            "blob_url": "https://gitlab.myteksi.net/test-group/test-project/-/blob/master/testsdk/testpb/test.swagger.json",
            "expected_result": fake_file_content,
        },
        {
            "blob_url": "https://gitlab.myteksi.net/test-group/test-project/-/blob/master/testsdk/testpb/test.swagger.txt",
            "expected_error": ValueError,
        },
    ]

    for test_case in test_cases:
        with patch("zion.util.gitlab.gl_client") as mock_gl_client:
            # Create a fake project
            project = MagicMock()
            mock_gl_client.projects.get.return_value = project

            # Create a fake file, its content and mock the method
            file = MagicMock()
            project.files.get.return_value = file
            file.decode.return_value = json.dumps(fake_file_content)
            from zion.util.gitlab import load_gitlab_file_in_dict

            # Grab a valid GitLab Blob URL
            blob_url = test_case["blob_url"]
            if "expected_result" in test_case:
                result = load_gitlab_file_in_dict(blob_url)
                assert result == test_case["expected_result"]
            elif "expected_error" in test_case:
                with pytest.raises(test_case["expected_error"]):
                    load_gitlab_file_in_dict(blob_url)


def test_get_gitlab_repo_name() -> None:
    test_cases = [
        {
            "gitlab_url": "https://gitlab.myteksi.net/techops-automation/gate/grabgpt-analytics",
            "expected_gitlab_repo_name": "techops-automation/gate/grabgpt-analytics",
        },
        {
            "gitlab_url": "https://gitlab.myteksi.net/techops-automation/gate/grabgpt-analytics/",
            "expected_gitlab_repo_name": "techops-automation/gate/grabgpt-analytics",
        },
        {
            "gitlab_url": "https://gitlab.myteksi.net/techops-automation/gate/grabgpt-analytics/-",
            "expected_gitlab_repo_name": "techops-automation/gate/grabgpt-analytics",
        },
        {
            "gitlab_url": "https://gitlab.myteksi.net/techops-automation/gate/grabgpt-analytics/-/",
            "expected_gitlab_repo_name": "techops-automation/gate/grabgpt-analytics",
        },
        {
            "gitlab_url": "https://gitlab.myteksi.net/gophers/go/-/tree/master/.conveyor/pipeline?ref_type=heads",
            "expected_gitlab_repo_name": "gophers/go",
        },
    ]
    for test_case in test_cases:
        repo_name = get_gitlab_repo_name(test_case["gitlab_url"])
        assert repo_name == test_case["expected_gitlab_repo_name"]
