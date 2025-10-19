import pytest

from zion.util.get_url_metadata.get_doc_type import DocumentType, get_doc_type


def test_confluence_document() -> None:
    url = "https://wiki.grab.com"
    expected = DocumentType.ConfluenceDocument
    result = get_doc_type(url)
    assert result == expected


def test_confluence_stg_document() -> None:
    url = "https://mockrun-confluence.stg-myteksi.com"
    expected = DocumentType.ConfluenceDocument
    result = get_doc_type(url)
    assert result == expected


def test_helix_entity() -> None:
    url = "https://helix-staging.stg.nexus.int.engtools.net/catalog/default/component/managed-eks"
    expected = DocumentType.HelixEntity
    result = get_doc_type(url)
    assert result == expected


def test_google_document() -> None:
    url = "https://docs.google.com"
    expected = DocumentType.GoogleDocument
    result = get_doc_type(url)
    assert result == expected


def test_helix_document_catalog() -> None:
    url = "https://helix-staging.stg.nexus.int.engtools.net/catalog/default/component/managed-eks/docs"
    expected = DocumentType.HelixDocument
    result = get_doc_type(url)
    assert result == expected


def test_helix_document() -> None:
    url = "https://helix-staging.stg.nexus.int.engtools.net/docs/default/Component/test-ls-3"
    expected = DocumentType.HelixDocument
    result = get_doc_type(url)
    assert result == expected


def test_other_document() -> None:
    url = "https:www.google.com"
    err_message = f"Invalid URL provided to get content: {url}"
    with pytest.raises(ValueError, match=err_message):
        get_doc_type(url)
