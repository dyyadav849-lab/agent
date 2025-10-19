import pytest

from zion.util.get_url_metadata.helix import (
    ExtractHelixEntityMetadata,
    ExtractHelixTechdocsContent,
    HelixEntityMetadata,
)


def test_extract_entity_request() -> None:
    # Test case 1: Extract metadata from url
    url = "https://helix.engtools.net/catalog/default/group/test-automation-mobile"
    expected_output = HelixEntityMetadata(
        namespace="default", kind="group", entity_name="test-automation-mobile"
    )
    assert ExtractHelixEntityMetadata().extract_entity_request(url) == expected_output

    # Test case 2: Check if the url is invalid
    url = "https://helix.engtools.net/catalog/default/group"
    err_message = f"Invalid Helix catalog url: {url}"
    with pytest.raises(ValueError, match=err_message):
        ExtractHelixEntityMetadata().extract_entity_request(url)


def test_extract_entity_metadata() -> None:
    # test case 1: Correct input dict
    helix_grp_entity = {
        "metadata": {
            "name": "test-group",
            "annotations": {
                "helix.engtools.net/engineering-lead": "John Doe",
                "helix.engtools.net/cto": "Jane Smith",
                "helix.engtools.net/business-lead": "Alice Johnson",
                "helix.engtools.net/product-lead": "Bob Williams",
                "helix.engtools.net/qa-lead": "Sarah Davis",
                "helix.engtools.net/service-channel": "support-channel",
                "helix.engtools.net/slack-channels": "channel1, channel2",
            },
            "description": "This is a test group",
        },
        "spec": {"owner": "John Smith"},
    }

    expected_output = """Entity Name: test-group
Engineering Lead: John Doe
Cto: Jane Smith
Business Lead: Alice Johnson
Product Lead: Bob Williams
Qa Lead: Sarah Davis
Catalog Description: This is a test group
Service Channel: support-channel
Slack Channels: channel1, channel2
Owner: John Smith
"""

    assert (
        ExtractHelixEntityMetadata().extract_entity_metadata(helix_grp_entity)
        == expected_output
    )

    # test case 2: Incorrect input dict for metadata.
    helix_grp_entity = {
        "metadata_incorrect": {
            "name": "test-group",
            "annotations": {
                "helix.engtools.net/engineering-lead": "John Doe",
                "helix.engtools.net/cto": "Jane Smith",
                "helix.engtools.net/business-lead": "Alice Johnson",
                "helix.engtools.net/product-lead": "Bob Williams",
                "helix.engtools.net/qa-lead": "Sarah Davis",
                "helix.engtools.net/service-channel": "support-channel",
                "helix.engtools.net/slack-channels": "channel1, channel2",
            },
            "description": "This is a test group",
        },
        "spec": {"profile": {"email": "test@example.com"}, "owner": "John Smith"},
    }

    expected_output = """Catalog Email: test@example.com
Owner: John Smith
"""

    assert (
        ExtractHelixEntityMetadata().extract_entity_metadata(helix_grp_entity)
        == expected_output
    )

    # test case 3: Incorrect input dict. Should return empty string
    helix_grp_entity = {
        "metadata_incorrect": {
            "name": "test-group",
            "annotations": {
                "helix.engtools.net/engineering-lead": "John Doe",
                "helix.engtools.net/cto": "Jane Smith",
                "helix.engtools.net/business-lead": "Alice Johnson",
                "helix.engtools.net/product-lead": "Bob Williams",
                "helix.engtools.net/qa-lead": "Sarah Davis",
                "helix.engtools.net/service-channel": "support-channel",
                "helix.engtools.net/slack-channels": "channel1, channel2",
            },
            "description": "This is a test group",
        },
        "spec_incorrect": {
            "profile": {"email": "test@example.com"},
            "owner": "John Smith",
        },
    }

    expected_output = ""

    assert (
        ExtractHelixEntityMetadata().extract_entity_metadata(helix_grp_entity)
        == expected_output
    )


def test_get_document_title_url() -> None:
    # test case 1: Test accessing doc from catalog
    url = "https://helix.engtools.net/catalog/default/component/techdocs-commenting/docs/faq"
    assert ExtractHelixTechdocsContent().get_document_title_url(url) == (
        "/default/component/techdocs-commenting/faq",
        "techdocs-commenting",
    )

    # test case 2: Test accessing doc from documentation
    url = "https://helix.engtools.net/docs/default/Component/bulletin-lifecycle-and-framework/platform"
    assert ExtractHelixTechdocsContent().get_document_title_url(url) == (
        "/default/Component/bulletin-lifecycle-and-framework/platform",
        "bulletin-lifecycle-and-framework",
    )

    # test case 3: Test invalid URL
    url = "https://helix.engtools.net/docs"
    assert ExtractHelixTechdocsContent().get_document_title_url(url) == ("", "")


def test_transform_relative_path() -> None:
    url = "https://helix.engtools.net/docs/default/Component/bulletin-lifecycle-and-framework/platform"

    # test case 1: Test if there is no relative path
    html_doc = '<a href="https://helix.engtools.net/catalog/default/component/techdocs-commenting/docs/faq">FAQ</a><p>Some text</p>'
    assert (
        ExtractHelixTechdocsContent().transform_relative_path(html_doc, "") == html_doc
    )

    # test case 2: Test if there is a header relative path
    html_doc = "<a href='#faq'>FAQ</a><p>Some text</p>"
    assert (
        ExtractHelixTechdocsContent().transform_relative_path(html_doc, url)
        == f'<a href="{url}#faq">FAQ</a><p>Some text</p>'
    )

    # test case 3: test if there is a relative path
    html_doc = "<a href='../faq'>FAQ</a><p>Some text</p>"
    assert (
        ExtractHelixTechdocsContent().transform_relative_path(html_doc, url)
        == '<a href="https://helix.engtools.net/docs/default/Component/bulletin-lifecycle-and-framework/faq">FAQ</a><p>Some text</p>'
    )
