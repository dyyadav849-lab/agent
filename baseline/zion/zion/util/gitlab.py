from __future__ import annotations

import json
import re
from typing import Any

import gitlab
import gitlab.const as gitlab_constant
import gitlab.v4.objects.groups as gitlab_groups
import gitlab.v4.objects.members as gitlab_members
import gitlab.v4.objects.projects as gitlab_projects
import yaml

from zion.config import global_config

GRAB_GITLAB_HOST = "https://gitlab.myteksi.net"

# the following are ti bot plugin repo variables
# the repo can be found here: https://gitlab.myteksi.net/techops-automation/gate/ti-bot-agent-plugins
TI_BOT_PLUGIN_REPO_ID = "22772"
TI_BOT_PLUGIN_REPO_MASTER_BRANCH = "master"
TI_BOT_PLUGIN_OPENAPI_FOLDER = "openapi-plugins"

GITLAB_CORRESPONDING_ACCESS_LEVEL_NAME = {
    gitlab_constant.AccessLevel.NO_ACCESS: "No Access",
    gitlab_constant.AccessLevel.MINIMAL_ACCESS: "Minimal Access",
    gitlab_constant.AccessLevel.GUEST: "Guest",
    gitlab_constant.AccessLevel.REPORTER: "Reporter",
    gitlab_constant.AccessLevel.ADMIN: "Admin",
    gitlab_constant.AccessLevel.DEVELOPER: "Developer",
    gitlab_constant.AccessLevel.MAINTAINER: "Maintainer",
    gitlab_constant.AccessLevel.OWNER: "Owner",
}


gitlab_blob_url_error = ValueError(
    "URL format is incorrect or not a valid GitLab blob URL"
)
gitlab_job_url_error = ValueError(
    "URL format is incorrect or not a valid GitLab job URL"
)
gitlab_url_error = ValueError("URL format is incorrect or not a valid GitLab repo URL")
gitlab_load_dict_error = ValueError("Only JSON and YAML files are supported")

gl_client = gitlab.Gitlab(
    url=GRAB_GITLAB_HOST, private_token=global_config.grab_gitlab_access_token
)


def get_project_groups(project_name: str) -> list[gitlab_projects.ProjectGroup]:
    """get_project_groups gets the gitlab group associated with a project ID
    The projects ID can either be the project id or project name
    """
    return gl_client.projects.get(project_name).groups.list(get_all=True, iterator=True)


def get_project_members(project_name: str) -> list[gitlab_members.ProjectMember]:
    """get_project_members gets the team members of a given project. Does not include those that has access to repo due to LDAP."""
    return gl_client.projects.get(project_name).members.list(
        get_all=True, iterator=True
    )


def get_group_details(group_id: int | str) -> gitlab_groups.Group:
    """get_group_details gets the details of a group"""
    return gl_client.groups.get(group_id)


def get_job_trace(project_name: str, job_id: str, num_lines: int) -> str:
    """Get the job trace for a specific project, and returns it in string"""
    project = gl_client.projects.get(project_name)

    job = project.jobs.get(job_id)

    gitlab_trace = job.trace().decode("utf-8")

    gitlab_trace_split = gitlab_trace.split("\n")

    return "\n".join(gitlab_trace_split[-num_lines:])


def is_gitlab_blob_url(blob_url: str) -> bool:
    """Check if the input path is a GitLab file path"""
    return blob_url.startswith(GRAB_GITLAB_HOST) and "/-/blob/" in blob_url


def load_gitlab_file_in_dict(blob_url: str) -> dict[str, Any]:
    """Load GitLab file from the given URL and return th content as a dictionary"""
    project_handle, branch_name, file_path = parse_gitlab_url(blob_url)

    # Get the project from GitLab
    project = gl_client.projects.get(project_handle)

    # Get the file from GitLab
    file = project.files.get(file_path, ref=branch_name)

    if file_path.endswith(".json"):
        return json.loads(file.decode())

    if file_path.endswith((".yml", ".yaml")):
        return yaml.safe_load(file.decode())

    raise gitlab_load_dict_error


# Input: https://gitlab.myteksi.net/techops-automation/helix-copilot/helix-copilot/-/blob/master/helixcopilotsdk/helixcopilotpb/helixcopilot.swagger.yml
# Output: techops-automation/helix-copilot/helix-copilot, master, helixcopilotsdk/helixcopilotpb/helixcopilot.swagger.yml
def parse_gitlab_url(url: str) -> tuple[str, str, str]:
    """
    Parse the given GitLab URL and return the project handle, branch name, and file path.
    """

    # Regex to extract necessary parts from the URL
    pattern = re.compile(
        r"https?:\/\/[^\/]+\/([^\/]+(?:\/[^\/]+)*)\/-\/blob\/([^\/]+)\/(.+)$"
    )
    match = pattern.match(url)

    if not match:
        raise gitlab_blob_url_error

    project_handle = match.group(1)
    branch_name = match.group(2)
    file_path = match.group(3)

    return project_handle, branch_name, file_path


def get_gitlab_repo_name(gitlab_url: str) -> str:
    """get_gitlab_link_id parses the gitlab url, and returns the gitlab project name"""

    # some gitlab link does not end with /-
    # this is when we first access a repo, and copy the link
    if "/-" not in gitlab_url:
        if gitlab_url.endswith("/"):
            gitlab_url += "-"
        else:
            gitlab_url += "/-"

    gitlab_url_regrex = "gitlab.myteksi.net/([.a-z0-9A-Z/-]*)/-"
    match = re.search(gitlab_url_regrex, gitlab_url)

    if match:
        # Extract the project name
        return match.group(1)

    raise gitlab_url_error


# Input: https://gitlab.myteksi.net/techops-automation/ti-support-bot/-/jobs/
# Output: techops-automation/ti-support-bot, 67291682
def parse_gitlab_job_url(gitlab_job_url: str) -> tuple[str, str]:
    """Returns the project_name, and job_id for a given gitlab job url"""
    gitlab_job_url_regrex = "gitlab.myteksi.net/([.a-z0-9A-Z/-]*)/-/jobs/([0-9]+)"

    match = re.search(gitlab_job_url_regrex, gitlab_job_url)

    if match:
        # Extract the project name and job ID
        project_name = match.group(1)
        job_id = match.group(2)

        return project_name, job_id

    raise gitlab_job_url_error


def get_files_folders_in_repository(
    folder_path: str, repo: str, branch_name: str
) -> list[dict[str, Any]]:
    """Returns the folders and files inside the given repository from Gitlab"""

    return gl_client.projects.get(repo).repository_tree(
        path=folder_path, ref=branch_name
    )


def get_file_content_for_repo(repo: str, file_path: str, branch_name: str) -> bytes:
    """Returns the file content for the given repository and branch from Gitlab"""
    file = gl_client.projects.get(repo).files.get(file_path=file_path, ref=branch_name)
    return file.decode()
