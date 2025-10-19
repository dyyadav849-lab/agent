from langchain_community.document_loaders import GoogleDriveLoader
from langchain_core.documents import Document

from zion.config import logger
from zion.credentials.google import GOOGLE_CREDENTIALS_FILE_LOCATION
from zion.util.constant import DocumentTitle, DocumentUri


def get_google_doc_document(google_doc_url: str) -> Document:
    """Gets the content of a gdoc given a link to a gdoc
    The service account is only able to access Grabbers (FTE).
    Example: https://docs.google.com/document/d/1ZRyREyug3oSklpzVqHSQTVf83QGt6PmLs_RceyPcvxY/edit
    Example Grab (cannot access): https://docs.google.com/document/d/1vMSBD2nlACTr1iL1mn69d87H9_036Vr4_uRt98qJdVo/edit
    """
    minimum_match_for_valid_doc_url = 6
    google_doc_link_coll = google_doc_url.split("/")
    if len(google_doc_link_coll) < minimum_match_for_valid_doc_url:
        err_message = f"Invalid Google Doc URL provided: {google_doc_url}"
        logger.error(err_message)
        raise ValueError(err_message)

    document: list[Document] = []
    google_documents: list[Document] = []

    google_doc_id = google_doc_link_coll[5]
    loader = GoogleDriveLoader(
        document_ids=[google_doc_id],
        service_account_key=GOOGLE_CREDENTIALS_FILE_LOCATION,
    )

    google_documents = loader.load()

    for google_document in google_documents:
        document = Document(
            page_content=google_document.page_content,
            metadata={
                DocumentTitle: google_document.metadata["title"],
                DocumentUri: google_document.metadata["source"],
            },
        )
    return document
