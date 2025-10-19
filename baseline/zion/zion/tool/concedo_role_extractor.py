from typing import Optional

from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.tools import BaseTool
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from zion.config import logger
from zion.util.presto import query_presto

GET_CONCEDO_ROLE_AND_APP_NAME_QUERY = "SELECT array_join(array_agg(concedo.concedo_iam_applications.name), ',') as app_name, array_join(array_agg(concedo.concedo_iam_roles.name), ',') as role, concedo.concedo_iam_ldap_groups.name as ldap_groups FROM concedo.role_ldap_groups INNER JOIN concedo.concedo_iam_roles ON concedo.concedo_iam_roles.role_id = concedo.role_ldap_groups.role_id INNER JOIN concedo.concedo_iam_ldap_groups ON concedo.concedo_iam_ldap_groups.group_id = concedo.role_ldap_groups.group_id INNER JOIN concedo.concedo_iam_applications ON concedo.concedo_iam_roles.app_id = concedo.concedo_iam_applications.app_id WHERE concedo.concedo_iam_ldap_groups.name in (%s) GROUP BY concedo.concedo_iam_ldap_groups.name "


class ConcedoRoleExtractorToolInput(BaseModel):
    ldap_groups_list: str = Field(
        description="List of LDAP Groups to get the corresponding Concedo Role for. Must be a comma separated string if passing in more than 1 LDAP Group"
    )


class ConcedoMetadata(BaseModel):
    concedo_role: str
    application_name: str


class ConcedoRoleExtractorTool(BaseTool):
    name: str = "concedo_role_extractor_from_ldap"
    description: str = "Used to get obtain all concedo roles to gain access to a ldap group, given a list of ldap group. "

    args_schema: type[BaseModel] = ConcedoRoleExtractorToolInput
    handle_tool_error: bool = True  # handle ToolExceptions

    def get_concedo_metadata_for_ldap(
        self, ldap_groups: list[str]
    ) -> dict[str, list[ConcedoMetadata]]:
        """get_concedo_metadata_for_ldap sets the concedo metadata based on the given ldap group details. Returns a new LdapGroupDetails that contains the collection of concedo metadata"""
        if len(ldap_groups) <= 0:
            return []

        # the valid concedo presto data is 2
        # this is because we have 3 metadata
        # 1. Concedo Application Name
        # 2. Concedo Role
        # 3. Associated LDAP Group
        valid_concedo_presto_data_length = 2

        ldap_group_collection_with_concedo_metadata: dict[
            str, list[ConcedoMetadata]
        ] = {}

        # query presto with the collection of ldap group names
        query = GET_CONCEDO_ROLE_AND_APP_NAME_QUERY % (
            ",".join([f"'{ldap_group_name}'" for ldap_group_name in ldap_groups])
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

            ldap_group_collection_with_concedo_metadata[ldap_group_for_concedo_role] = [
                ConcedoMetadata(
                    application_name=application_name_collection[index],
                    concedo_role=concedo_role,
                )
                for index, concedo_role in enumerate(concedo_role_collection)
            ]

        return ldap_group_collection_with_concedo_metadata

    def get_ldap_group_message_needed(
        self,
        ldap_group_detail: dict[str, list[ConcedoMetadata]],
    ) -> str:
        """get_ldap_group_message_needed returns the concedo role, along with application name that user needs to apply for a given ldap group"""

        return "\n".join(
            [
                f"User can try to apply the following Concedo role: {', '.join([f'{concedo_role.application_name} -> {concedo_role.concedo_role}' for concedo_role in ldap_group_detail[ldap_group]])} to get access to the ldap group: {ldap_group}"
                for ldap_group in ldap_group_detail
            ]
        )

    def concedo_role_extractor_tool(
        self,
        ldap_groups_list: str,
    ) -> str:
        """Used to get obtain concedo role, given a list of ldap group."""
        try:
            return self.get_ldap_group_message_needed(
                self.get_concedo_metadata_for_ldap(ldap_groups_list.split(","))
            )

        except Exception as e:
            err_message = f"Unable to perform gitlab access check with error: {e!s}"
            logger.exception(err_message)
            raise ToolException(err_message) from e

    def _run(
        self,
        ldap_groups_list: str,
        _: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Used to get obtain concedo role, given a list of ldap group."""
        return self.concedo_role_extractor_tool(ldap_groups_list)

    async def _arun(
        self,
        ldap_groups_list: str,
        _: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Used to get obtain concedo role, given a list of ldap group."""
        return self.concedo_role_extractor_tool(ldap_groups_list)
