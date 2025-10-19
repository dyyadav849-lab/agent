import yaml

from zion.data.agent_plugin.database_handler import (
    save_agent_plugin_to_db,
    set_all_plugin_to_is_moved,
)
from zion.util.gitlab import (
    TI_BOT_PLUGIN_OPENAPI_FOLDER,
    TI_BOT_PLUGIN_REPO_ID,
    TI_BOT_PLUGIN_REPO_MASTER_BRANCH,
    get_file_content_for_repo,
    get_files_folders_in_repository,
)

JOB_NAME_SYNC_AGENT_PLUGIN = "sync_agent_plugin"


def sync_agent_plugin() -> None:
    """Syncs the agent plugin from gitlab repository into the table `agent_plugin`. Stores all data such as access_control and include_paths.

    Refer to this repository (https://gitlab.myteksi.net/techops-automation/gate/ti-bot-agent-plugins/-/tree/master/openapi-plugins/ti-support-bot?ref_type=heads) for a predefined specification
    """

    # set all plugins as is moved in database
    set_all_plugin_to_is_moved()

    openapi_plugins = get_files_folders_in_repository(
        folder_path=TI_BOT_PLUGIN_OPENAPI_FOLDER,
        branch_name=TI_BOT_PLUGIN_REPO_MASTER_BRANCH,
        repo=TI_BOT_PLUGIN_REPO_ID,
    )

    if openapi_plugins is None or len(openapi_plugins) == 0:
        # there is no plugin to be synced into DB, we abort the job
        return

    for plugin in openapi_plugins:
        folder_name = plugin.get("name", "")
        if folder_name == "":
            continue

        # get the files inside the folder
        folder_path = f"{TI_BOT_PLUGIN_OPENAPI_FOLDER}/{folder_name}"

        yaml_files = get_files_folders_in_repository(
            folder_path=folder_path,
            branch_name=TI_BOT_PLUGIN_REPO_MASTER_BRANCH,
            repo=TI_BOT_PLUGIN_REPO_ID,
        )

        if yaml_files is None or len(openapi_plugins) == 0:
            # there is no yaml files to be synced into DB, we ignore this folder path
            continue

        for yaml_file in yaml_files:
            file_name = yaml_file.get("name", "")

            if file_name == "":
                # we ignore file name that are empty
                continue

            # get the yaml file from gitlab
            file_content_str = get_file_content_for_repo(
                branch_name=TI_BOT_PLUGIN_REPO_MASTER_BRANCH,
                file_path=f"{folder_path}/{file_name}",
                repo=TI_BOT_PLUGIN_REPO_ID,
            )

            file_content_yaml = yaml.safe_load(file_content_str)

            # store the file content into database, if not update it
            save_agent_plugin_to_db(file_content_yaml)
