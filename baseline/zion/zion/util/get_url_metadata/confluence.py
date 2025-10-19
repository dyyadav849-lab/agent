from urllib.parse import parse_qs, unquote, urlparse

from langchain_community.document_loaders import ConfluenceLoader
from langchain_core.documents import Document

from zion.config import global_config, logger
from zion.util.constant import DocumentTitle, DocumentUri
from zion.util.get_url_metadata.util import clean_url


class ExtractConfluenceDocument:
    def query_confluence_with_page_id_url(
        self, confluence_doc_url: str, confluence_loader: ConfluenceLoader
    ) -> Document:
        """Gets the document content based on the url page ID
        the confluence page might be referenced using page id
        example: https://wiki.grab.com/pages/viewpage.action?pageId=538979403
        staging example: https://mockrun-confluence.stg-myteksi.com/pages/viewpage.action?pageId=468799012
        """
        parsed_confluence_url = urlparse(confluence_doc_url)
        confluence_url_params = parse_qs(parsed_confluence_url.query)

        param_page_id = confluence_url_params["pageId"]

        if len(param_page_id) <= 0:
            err_msg = f"Invalid Confluence Doc URL {confluence_doc_url}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        # extract the pageId
        page_id = param_page_id[0]

        return confluence_loader.load(
            page_ids=[page_id],
            include_comments=True,
            include_attachments=False,
            keep_markdown_format=True,
        )

    def query_confluence_with_page_title_url(
        self, confluence_doc_url: str, confluence_loader: ConfluenceLoader
    ) -> Document:
        """Gets the document content based on the url page title
        the confluence might be referenced using document title
        example: https://wiki.grab.com/display/SWAT/RFC%3A+TI+Bot+Agent
        staging example: https://mockrun-confluence.stg-myteksi.com/display/~adam.chin/Test+Plugins+on+jira+Staging
        """
        cleaned_url = clean_url(confluence_doc_url)

        # get the last element from the url, attempt to access it
        split_clean_url = cleaned_url.split("/")
        page_title = unquote(split_clean_url[len(split_clean_url) - 1]).replace(
            "+", " "
        )
        return confluence_loader.load(
            cql=f"title='{page_title}'",
            include_comments=True,
            include_attachments=False,
            keep_markdown_format=True,
        )

    def get_confluence_doc_document(self, confluence_doc_url: str) -> Document:
        """Gets the document content for a given confluence link"""
        confluence_loader = ConfluenceLoader(
            url=global_config.confluence_base_url,
            username=global_config.confluence_username,
            api_key=global_config.confluence_password,
            cloud=False,
        )
        documents: list[Document] = []

        if "?pageId=" in confluence_doc_url:
            documents = self.query_confluence_with_page_id_url(
                confluence_doc_url=confluence_doc_url,
                confluence_loader=confluence_loader,
            )
        else:
            documents = self.query_confluence_with_page_title_url(
                confluence_doc_url=confluence_doc_url,
                confluence_loader=confluence_loader,
            )

        return Document(
            page_content=documents[0].page_content,
            metadata={
                DocumentTitle: documents[0].metadata["title"],
                DocumentUri: documents[0].metadata["source"],
            },
        )
