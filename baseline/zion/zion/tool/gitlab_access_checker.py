from enum import Enum
from typing import Optional

import gitlab.const as gitlab_constant
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.tools import BaseTool
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from zion.config import logger
from zion.util.gitlab import (
    GITLAB_CORRESPONDING_ACCESS_LEVEL_NAME,
    get_gitlab_repo_name,
    get_group_details,
    get_project_groups,
    get_project_members,
)
from zion.util.presto import query_presto

GET_CONCEDO_ROLE_AND_APP_NAME_QUERY = "SELECT array_join(array_agg(concedo.concedo_iam_applications.name), ',') as app_name, array_join(array_agg(concedo.concedo_iam_roles.name), ',') as role, concedo.concedo_iam_ldap_groups.name as ldap_groups FROM concedo.role_ldap_groups INNER JOIN concedo.concedo_iam_roles ON concedo.concedo_iam_roles.role_id = concedo.role_ldap_groups.role_id INNER JOIN concedo.concedo_iam_ldap_groups ON concedo.concedo_iam_ldap_groups.group_id = concedo.role_ldap_groups.group_id INNER JOIN concedo.concedo_iam_applications ON concedo.concedo_iam_roles.app_id = concedo.concedo_iam_applications.app_id WHERE concedo.concedo_iam_ldap_groups.name in (%s) GROUP BY concedo.concedo_iam_ldap_groups.name "


class GitlabAccessIssue(Enum):
    INABILITY_TO_TRIGGER_PIPELINE = "inability_to_trigger_pipeline"
    INABILITY_TO_MERGE = "inability_to_merge"
    INABILITY_TO_PUSH_CODE_TO_REPO = "inability_to_push_code_to_repository"
    INABILITY_TO_VIEW_OR_CLONE_REPO = "inability_to_view_or_clone_repository"
    NONE = "none"


class GitlabRepositoryAccessCheckerInput(BaseModel):
    gitlab_repo_link: str = Field(
        description="Link to the Gitlab Repository, that user is facing difficulty performing action"
    )
    issue_access_type: str = Field(
        description=f"Can only be {GitlabAccessIssue.INABILITY_TO_TRIGGER_PIPELINE.value}, {GitlabAccessIssue.INABILITY_TO_MERGE.value}, {GitlabAccessIssue.INABILITY_TO_PUSH_CODE_TO_REPO.value} or {GitlabAccessIssue.INABILITY_TO_VIEW_OR_CLONE_REPO.value}. Default value is {GitlabAccessIssue.NONE.value} for other requests, or to get the repository access level, concedo role details and LDAP Group"
    )


class ConcedoMetadata(BaseModel):
    concedo_role: str
    application_name: str


class LdapGroupDetails(BaseModel):
    ldap_group_name: str
    gitlab_access_level: int
    concedo_metadata: Optional[list[ConcedoMetadata]]


class MemberAccessLevel(BaseModel):
    member_name: str
    member_access_level: int


class GitlabGroupDetails(BaseModel):
    gitlab_group_name: Optional[str]
    allow_to_push_level: Optional[int]
    allow_to_merge_level: Optional[int]
    ldap_group_details: Optional[list[LdapGroupDetails]]


class RepoAccessDetails(BaseModel):
    gitlab_project_owners: list[MemberAccessLevel]
    gitlab_group_details: list[GitlabGroupDetails]


class GitlabRepositoryAccessCheckerTool(BaseTool):
    name: str = "gitlab_repository_access_checker_tool"
    description: str = "Used to get data on Gitlab Repository that user has access issue to, either for inability to trigger CI Pipeline, Merge merge request, push code to a repository or view or clone a repository. Can also be called to get all the ldap groupes or owner related to a repository."

    args_schema: type[BaseModel] = GitlabRepositoryAccessCheckerInput
    handle_tool_error: bool = True  # handle ToolExceptions

    def get_access_level_details(
        self, default_branch_protection_defaults: dict, access_level_key: str
    ) -> int:
        """get_access_level_details gets the access level detail for a given gitlab group."""

        access_level_data = default_branch_protection_defaults.get(access_level_key, [])

        if len(access_level_data) > 0:
            return access_level_data[0].get(
                "access_level", gitlab_constant.AccessLevel.NO_ACCESS
            )

        return gitlab_constant.AccessLevel.NO_ACCESS

    def set_concedo_metadata_for_ldap(
        self, ldap_group_collection: list[LdapGroupDetails]
    ) -> list[LdapGroupDetails]:
        """set_concedo_metadata_for_ldap sets the concedo metadata based on the given ldap group details. Returns a new LdapGroupDetails that contains the collection of concedo metadata"""
        if len(ldap_group_collection) <= 0:
            return ldap_group_collection

        default_ldap_group_detail = LdapGroupDetails(
            ldap_group_name="", gitlab_access_level=gitlab_constant.NO_ACCESS
        )

        # the valid concedo presto data is 2
        # this is because we have 3 metadata
        # 1. Concedo Application Name
        # 2. Concedo Role
        # 3. Associated LDAP Group
        valid_concedo_presto_data_length = 2

        ldap_group_collection_with_concedo_metadata: list[LdapGroupDetails] = []

        # get the names of ldap group for querying presto
        ldap_group_names: list[str] = []

        # create a new map of ldap group collection
        # so we can get back the original ldap group
        ldap_group_coll_map = {}
        for ldap_group in ldap_group_collection:
            ldap_group_coll_map[ldap_group.ldap_group_name] = ldap_group
            ldap_group_names.append(ldap_group.ldap_group_name)

        # query presto with the collection of ldap group names
        query = GET_CONCEDO_ROLE_AND_APP_NAME_QUERY % (
            ",".join([f"'{ldap_group_name}'" for ldap_group_name in ldap_group_names])
        )
        presto_result = query_presto(query)

        for single_ldap_presto_result in presto_result:
            if len(single_ldap_presto_result) < valid_concedo_presto_data_length:
                # we will also ignore ldap group that user cant get the concedo application to access since it adds no purpose
                continue

            # the first result will always be the application name
            application_name_collection = single_ldap_presto_result[0].split(",")

            # the second result will the concedo role collection
            concedo_role_collection = single_ldap_presto_result[1].split(",")

            # the last result will be the ldap group associated with it
            ldap_group_for_concedo_role = single_ldap_presto_result[2]

            ldap_group_collection_with_concedo_metadata.append(
                # create a new ldap group details with the concedo metadata
                LdapGroupDetails(
                    concedo_metadata=[
                        ConcedoMetadata(
                            application_name=application_name_collection[index],
                            concedo_role=concedo_role,
                        )
                        for index, concedo_role in enumerate(concedo_role_collection)
                    ],
                    ldap_group_name=ldap_group_coll_map.get(
                        ldap_group_for_concedo_role, default_ldap_group_detail
                    ).ldap_group_name,
                    gitlab_access_level=ldap_group_coll_map.get(
                        ldap_group_for_concedo_role, default_ldap_group_detail
                    ).gitlab_access_level,
                )
            )

        return ldap_group_collection_with_concedo_metadata

    def get_gitlab_access_metadata(self, gitlab_repo_link: str) -> RepoAccessDetails:
        """get_gitlab_access_metadata gets all the metadata related to access to the gitlab repo
        This includes the Ldap group and Grabbers who have access level to a project. Does not include user who have ldap group access to the repo"""
        gitlab_repo_name = get_gitlab_repo_name(gitlab_repo_link)
        gitlab_groups = get_project_groups(gitlab_repo_name)
        gitlab_project_members = get_project_members(gitlab_repo_name)

        gitlab_group_data_collection: list[GitlabGroupDetails] = []
        for gitlab_group in gitlab_groups:
            gitlab_group_cleanup_detail: GitlabGroupDetails = GitlabGroupDetails()

            ldap_group_collection: list[LdapGroupDetails] = []

            # set the gitlab group name
            gitlab_group_cleanup_detail.gitlab_group_name = gitlab_group.attributes.get(
                "full_path", ""
            )

            # get the gitlab group details
            gitlab_group_details = get_group_details(gitlab_group.get_id())

            default_branch_protection_defaults = gitlab_group_details.attributes.get(
                "default_branch_protection_defaults", {}
            )

            # set the permission for allow to merge
            gitlab_group_cleanup_detail.allow_to_merge_level = (
                self.get_access_level_details(
                    default_branch_protection_defaults, "allowed_to_merge"
                )
            )

            # set the permission for allow to push
            gitlab_group_cleanup_detail.allow_to_push_level = (
                self.get_access_level_details(
                    default_branch_protection_defaults, "allowed_to_push"
                )
            )

            main_ldap_name = gitlab_group_details.attributes.get("ldap_cn", {})
            main_ldap_access = gitlab_group_details.attributes.get("ldap_access", {})

            if main_ldap_name is not None and main_ldap_access is not None:
                ldap_group_collection.append(
                    LdapGroupDetails(
                        gitlab_access_level=main_ldap_access,
                        ldap_group_name=main_ldap_name,
                    )
                )

            sub_ldap_collection = gitlab_group_details.attributes.get(
                "ldap_group_links", {}
            )

            for sub_ldap in sub_ldap_collection:
                ldap_group_name = sub_ldap.get("cn", "")
                ldap_group_access = sub_ldap.get(
                    "group_access", gitlab_constant.AccessLevel.NO_ACCESS
                )

                if ldap_group_name is not None and ldap_group_access is not None:
                    ldap_group_collection.append(
                        LdapGroupDetails(
                            gitlab_access_level=ldap_group_access,
                            ldap_group_name=ldap_group_name,
                        )
                    )
            gitlab_group_cleanup_detail.ldap_group_details = (
                self.set_concedo_metadata_for_ldap(ldap_group_collection)
            )
            gitlab_group_data_collection.append(gitlab_group_cleanup_detail)

        cleaned_gitlab_member_data = [
            MemberAccessLevel(
                member_name=gitlab_member.attributes.get("username", ""),
                member_access_level=gitlab_member.attributes.get(
                    "access_level", gitlab_constant.AccessLevel.NO_ACCESS
                ),
            )
            # we iterate through all the project owners
            for gitlab_member in gitlab_project_members
            # we check that the owners is owner/maintainer
            # this is because only owner/maintainer can add user to a repo/update a repo
            if any(
                access_level
                <= gitlab_member.attributes.get(
                    "access_level", gitlab_constant.AccessLevel.NO_ACCESS
                )
                for access_level in [
                    gitlab_constant.MAINTAINER_ACCESS,
                    gitlab_constant.OWNER_ACCESS,
                ]
            )
            and gitlab_member.attributes.get("state", "") == "active"
            and gitlab_member.attributes.get("membership_state", "") == "active"
        ]

        return RepoAccessDetails(
            gitlab_project_owners=cleaned_gitlab_member_data,
            gitlab_group_details=gitlab_group_data_collection,
        )

    def get_ldap_group_message_needed(
        self,
        repo_access_details: RepoAccessDetails,
        access_level_code_needed: list[int],
    ) -> list[str]:
        """get_ldap_group_message_needed returns the ldap group message based on the access level user have"""
        return [
            f"User can try to apply the following Concedo role: {', '.join([f'`{ldap_concedo_metadata.application_name} -> {ldap_concedo_metadata.concedo_role}`' for ldap_concedo_metadata in ldap_group.concedo_metadata])} to get {GITLAB_CORRESPONDING_ACCESS_LEVEL_NAME[ldap_group.gitlab_access_level]} role via the {ldap_group.ldap_group_name} LDAP Group"
            # we iterate through all the gitlab group of a gitlab project
            for gitlab_group_data in repo_access_details.gitlab_group_details
            # we iterate each ldap group for the gitlab group
            for ldap_group in gitlab_group_data.ldap_group_details
            # we check that the access level for the gitlab group is more or equal to the access level that user needs
            if any(
                access_level <= ldap_group.gitlab_access_level
                for access_level in access_level_code_needed
            )
            and len(ldap_group.concedo_metadata) > 0
            # we also check that the concedo role exist for the given ldap group, so that user can go and request access for it
        ]

    def get_gitlab_access_message(
        self,
        repo_access_details: RepoAccessDetails,
        issue_access_type: str = GitlabAccessIssue.NONE.value,
    ) -> str:
        """get_gitlab_access_message creates a message based on the ldap group and owner of the project for the tool."""
        # the min access for merge and push code to repo is different for each project
        # https://docs.gitlab.com/ee/user/permissions.html

        access_level_code_needed: list[int] = []
        match issue_access_type:
            case GitlabAccessIssue.INABILITY_TO_TRIGGER_PIPELINE.value:
                # the min access to trigger pipeline is developer
                access_level_code_needed.append(gitlab_constant.DEVELOPER_ACCESS)
            case GitlabAccessIssue.INABILITY_TO_MERGE.value:
                access_level_code_needed = access_level_code_needed + [
                    gitlab_group_data.allow_to_merge_level
                    for gitlab_group_data in repo_access_details.gitlab_group_details
                ]

            case GitlabAccessIssue.INABILITY_TO_PUSH_CODE_TO_REPO.value:
                access_level_code_needed = access_level_code_needed + [
                    gitlab_group_data.allow_to_push_level
                    for gitlab_group_data in repo_access_details.gitlab_group_details
                ]

            case GitlabAccessIssue.INABILITY_TO_VIEW_OR_CLONE_REPO.value:
                # the min access to view/clone repository is reporter
                access_level_code_needed.append(gitlab_constant.REPORTER_ACCESS)
            case GitlabAccessIssue.NONE.value:
                # this is for getting only the LDAP group/owner of a repo
                return f"The following is the repository access details, including LDAP Group and the project owners: {repo_access_details.__str__}"

        ldap_group_user_need = self.get_ldap_group_message_needed(
            repo_access_details=repo_access_details,
            access_level_code_needed=access_level_code_needed,
        )

        message_for_user = "\n".join(ldap_group_user_need)
        if len(repo_access_details.gitlab_project_owners) > 0:
            message_for_user += f"\nUser can also try to contact the following Grabbers as they have the corresponding access to the repository: {', '.join([repo_owner.member_name for repo_owner in repo_access_details.gitlab_project_owners])}"
        return message_for_user

    def gitlab_access_checker_tool(
        self, gitlab_repo_link: str, issue_access_type: str
    ) -> str:
        """Used to get data on Gitlab Repository that user has access issue to, either for inability to trigger CI Pipeline, Merge MR or Push code to the Repo."""
        try:
            return self.get_gitlab_access_message(
                self.get_gitlab_access_metadata(gitlab_repo_link), issue_access_type
            )

        except Exception as e:
            err_message = f"Unable to perform gitlab access check with error: {e!s}"
            logger.exception(err_message)
            raise ToolException(err_message) from e

    def _run(
        self,
        gitlab_repo_link: str,
        issue_access_type: str = GitlabAccessIssue.NONE.value,
        _: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Used to get data on Gitlab Repository that user has access issue to, either for inability to trigger CI Pipeline, Merge merge request, push code to a repository or view or clone a repository. Can also be called to get all the ldap groupes or owner related to a repository."""
        return self.gitlab_access_checker_tool(gitlab_repo_link, issue_access_type)

    async def _arun(
        self,
        gitlab_repo_link: str,
        issue_access_type: str = GitlabAccessIssue.NONE.value,
        _: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Used to get data on Gitlab Repository that user has access issue to, either for inability to trigger CI Pipeline, Merge merge request, push code to a repository or view or clone a repository. Can also be called to get all the ldap groupes or owner related to a repository."""
        return self.gitlab_access_checker_tool(gitlab_repo_link, issue_access_type)
