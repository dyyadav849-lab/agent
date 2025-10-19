from enum import Enum
from typing import Literal
from urllib.parse import urlparse


class DocumentType(str, Enum):
    """Document Type Enum"""

    ConfluenceDocument = "confluence"
    HelixDocument = "helix_document"
    HelixEntity = "helix_entity"
    GoogleDocument = "google_docs"

    def __str__(self) -> str:
        return str(self.value)


def get_doc_type(
    url: str,
) -> Literal[
    DocumentType.ConfluenceDocument,
    DocumentType.HelixEntity,
    DocumentType.GoogleDocument,
    DocumentType.HelixDocument,
]:
    """Gets the document type for the url given
    The document type returned is based on the enum DocumentType
    """
    parsed_url = urlparse(url)
    url_domain = f"{parsed_url.scheme}://{parsed_url.netloc}/"

    url_mapping = {
        "wiki.grab.com": DocumentType.ConfluenceDocument,
        "mockrun-confluence.stg-myteksi.com": DocumentType.ConfluenceDocument,
        "docs.google.com": DocumentType.GoogleDocument,
        "helix.engtools.net": DocumentType.HelixEntity
        if "/docs" not in url
        else DocumentType.HelixDocument,
        "helix-staging.stg.nexus.int.engtools.net": DocumentType.HelixEntity
        if "/docs" not in url
        else DocumentType.HelixDocument,
    }

    for key, value in url_mapping.items():
        if key in url_domain:
            return value

    err_message = f"Invalid URL provided to get content: {url}"
    raise ValueError(err_message)
