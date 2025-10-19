import re
from dataclasses import dataclass
from typing import Any

import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document

from zion.config import global_config, logger
from zion.tool.universal_search import HTTP_OK_STATUS
from zion.util import helix
from zion.util.constant import DocumentTitle, DocumentUri
from zion.util.get_url_metadata.util import convert_html_to_markdown, remove_html_tags


@dataclass
class HelixEntityMetadata:
    namespace: str
    kind: str
    entity_name: str


class ExtractHelixEntityMetadata:
    """Returns entity metadata, extracted from helix entity URL."""

    def extract_entity_request(self, entity_url: str) -> HelixEntityMetadata:
        """Extracts the request to call Helix from entity URL
        example:
            https://helix.engtools.net/catalog/default/group/test-automation-mobile
            Match 0: helix-staging.engtools.net
            Match 1:
            Match 2: default
            Match 3: group
            Match 4: test-automation-mobile
        """
        pattern = r"https:\/\/(helix(-staging\.stg\.nexus\.int)?\.engtools\.net)\/catalog\/(.*)\/(.*)\/(.*)"
        matches = re.findall(pattern, entity_url)

        minimum_pattern_for_valid_entity_url = 5

        if len(matches) < 1 or len(matches[0]) < minimum_pattern_for_valid_entity_url:
            err_message = f"Invalid Helix catalog url: {entity_url}"
            logger.error(err_message)
            raise ValueError(err_message)

        return HelixEntityMetadata(
            namespace=matches[0][2],
            kind=matches[0][3],
            entity_name=matches[0][4],
        )

    def query_for_entity_metadata(
        self,
        helix_entity_metadata: HelixEntityMetadata,
        concedo_token: str,
        helix_token: str,
    ) -> dict[str, Any]:
        """calls helix to get helix entity metadata"""
        api_endpoint = f"/api/catalog/entities/by-name/{helix_entity_metadata.kind}/{helix_entity_metadata.namespace}/{helix_entity_metadata.entity_name}"

        res = requests.get(
            url=f"{global_config.helix_base_url}{api_endpoint}",
            headers={
                "x-auth-concedo-token": concedo_token,
                "Authorization": f"Bearer {helix_token}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        if res.reason != HTTP_OK_STATUS:
            err_msg = f"Kendra 'query_for_entity_metadata' failed with status code `{res.status_code}` and reason `{res.reason}`, response: {res.text}"
            logger.error(err_msg)
            raise ConnectionError(err_msg)

        return res.json()

    def extract_entity_metadata(
        self,
        helix_grp_entity: dict[str, Any],
    ) -> dict[str, Any]:
        """Extracts entity metadata to be passed to GPT. Will not include empty fields"""
        helix_metadata_str: str = ""
        gpt_tags = [
            "Entity Name",
            "Engineering Lead",
            "Cto",
            "Cto-1",
            "Business Lead",
            "Product Lead",
            "Data Science Lead",
            "Design Lead",
            "Tpm Lead",
            "Analytics Lead",
            "Other Leaders",
            "Security Partner",
            "Security Champion",
            "Project Board",
            "Wiki Page",
            "Qa Lead",
            "Catalog Description",
            "Catalog Email",
            "Oncall Handler",
            "Oncall Tag",
            "Service Channel",
            "Service Wiki",
            "Slack Channels",
            "Owner",
        ]
        helix_grp_entity_metadata = helix_grp_entity.get("metadata", {})
        helix_grp_entity_annotations = helix_grp_entity_metadata.get("annotations", {})
        helix_entity_metadatas_spec = helix_grp_entity.get("spec", {})
        helix_entity_metadatas = [
            helix_grp_entity_metadata.get("name", ""),
            helix_grp_entity_annotations.get("helix.engtools.net/engineering-lead", ""),
            helix_grp_entity_annotations.get("helix.engtools.net/cto", ""),
            helix_grp_entity_annotations.get("helix.engtools.net/cto-1", ""),
            helix_grp_entity_annotations.get("helix.engtools.net/business-lead", ""),
            helix_grp_entity_annotations.get("helix.engtools.net/product-lead", ""),
            helix_grp_entity_annotations.get(
                "helix.engtools.net/data-science-lead", ""
            ),
            helix_grp_entity_annotations.get("helix.engtools.net/design-lead", ""),
            helix_grp_entity_annotations.get("helix.engtools.net/tpm-lead", ""),
            helix_grp_entity_annotations.get("helix.engtools.net/analytics-lead", ""),
            helix_grp_entity_annotations.get("helix.engtools.net/other-leaders", ""),
            helix_grp_entity_annotations.get("helix.engtools.net/security-partner", ""),
            helix_grp_entity_annotations.get(
                "helix.engtools.net/security-champion", ""
            ),
            helix_grp_entity_annotations.get("helix.engtools.net/project-board", ""),
            helix_grp_entity_annotations.get("helix.engtools.net/wiki-page", ""),
            helix_grp_entity_annotations.get("helix.engtools.net/qa-lead", ""),
            helix_grp_entity_metadata.get("description", ""),
            helix_entity_metadatas_spec.get("profile", {}).get("email", ""),
            helix_grp_entity_annotations.get(
                "helix.engtools.net/service-oncall-handle", ""
            ),
            helix_grp_entity_annotations.get("helix.engtools.net/oncall-tag", ""),
            helix_grp_entity_annotations.get("helix.engtools.net/service-channel", ""),
            helix_grp_entity_annotations.get("helix.engtools.net/service-wiki", ""),
            helix_grp_entity_annotations.get("helix.engtools.net/slack-channels", ""),
            helix_entity_metadatas_spec.get("owner", ""),
        ]
        for index, gpt_tag in enumerate(gpt_tags):
            helix_entity_metadata_gpt = helix_entity_metadatas[index]
            if helix_entity_metadata_gpt != "":
                helix_metadata_str += f"{gpt_tag}: {helix_entity_metadata_gpt}\n"

        return helix_metadata_str

    def get_entity_metadata(self, entity_url: str) -> Document:
        """Gets entity metadata from helix, given any URL to helix entity
        Is the main function to get entity metadata from helix
        """

        helix_entity_request: HelixEntityMetadata

        helix_entity_request = self.extract_entity_request(entity_url)

        concedo_token = ""
        helix_token = ""

        # calls helix to get helix token
        concedo_token, helix_token = helix.get_helix_token()

        # calls helix to get helix entity metadata
        helix_grp_entity = self.query_for_entity_metadata(
            helix_entity_request, concedo_token, helix_token
        )

        helix_grp_entity_gpt = self.extract_entity_metadata(helix_grp_entity)
        return Document(
            page_content=helix_grp_entity_gpt,
            metadata={
                DocumentTitle: helix_entity_request.entity_name,
                DocumentUri: entity_url,
            },
        )


class ExtractHelixTechdocsContent:
    """Returns helix techdocs content from helix extracted via techdocs URL"""

    def get_document_title_url(self, document_url: str) -> tuple[str, str]:
        """Gets the document title url (for calling kendra) and the document title from the URL
        Returns (document_title_url, document_title)
        """

        # the 7th element is always the doc title
        doc_title_index = 7

        # we ignore the first 3 elements
        url_title_to_ignore = 3

        # split the document url from the / and get the document title url
        split_url_collection = document_url.split("/")
        document_title = ""
        document_title_url = ""
        for index, split_url in enumerate(split_url_collection):
            if index <= url_title_to_ignore or split_url == "docs":
                continue
            document_title_url += f"/{split_url}"

        if len(split_url_collection) >= doc_title_index:
            document_title = split_url_collection[6]

        return document_title_url, document_title

    def query_helix_for_techdocs(self, document_title_url: str) -> str:
        """Calls kendra to get techdocs content
        The url given here must be processed by "get_document_title_url" if the url given is raw
        """

        concedo_token, helix_token = helix.get_helix_token()

        url_to_query = f"{global_config.helix_base_url}/api/techdocs/static/docs{document_title_url}/index.html"
        res = requests.get(
            url=url_to_query,
            headers={
                "x-auth-concedo-token": concedo_token,
                "Authorization": f"Bearer {helix_token}",
            },
            timeout=10,
        )

        if res.reason != HTTP_OK_STATUS:
            err_msg = f"Kendra 'query_helix_for_techdocs' failed with status code `{res.status_code}` and reason `{res.reason}`, response: {res.text}"
            logger.error(err_msg)
            raise ConnectionError(err_msg)

        return res.text

    def get_helix_techdocs_content(self, helix_techdocs_url: str) -> Document:
        """Gets techdocs content from helix, given any URL to helix techdocs. Is the main function to get the techdocs content from helix"""
        # get the document title url to query helix
        # we also get the document title from the document
        document_title_url, document_title = self.get_document_title_url(
            helix_techdocs_url
        )

        # get the s3 content from helix
        s3_html_content = self.query_helix_for_techdocs(document_title_url)

        # transform all the url inside the doc to a relative path
        s3_html_content_transformed = self.transform_relative_path(
            s3_html_content, helix_techdocs_url
        )

        # remove html tags that wont be useful to GPT
        html_content_clean = remove_html_tags(s3_html_content_transformed)

        # convert html to markdown
        markdown_document = convert_html_to_markdown(html_content_clean)

        return Document(
            page_content=markdown_document,
            metadata={
                DocumentTitle: document_title,
                DocumentUri: helix_techdocs_url,
            },
        )

    def transform_relative_path(self, s3_html_content: str, document_url: str) -> str:
        """Transforms local path to a relative path
        For example, we will transform <a href = "#data"> -> "document_url#data"
        We will also transform local url <a href = "folder/file_name"> -> document_url/folder/filename
        """
        html_soup = BeautifulSoup(s3_html_content, "html.parser")
        for a in html_soup.find_all("a", href=True):
            if a["href"].startswith("#"):
                # replace # with url
                a["href"] = f"{document_url}{a['href']}"
                continue

            if (
                a["href"].startswith("https")
                or a["href"].startswith("http")
                or a["href"].startswith("www")
            ):
                # is a valid url, ignore
                continue

            # relative path
            document_url_split = document_url.split("/")
            href_split_collection = a["href"].split("/")
            for href_split in href_split_collection:
                # contains going to above folder, remove from document url
                if href_split == "..":
                    document_url_split.pop()
                else:
                    # adds to document url
                    document_url_split.append(href_split)
            a["href"] = "/".join(document_url_split)
        return str(html_soup)
