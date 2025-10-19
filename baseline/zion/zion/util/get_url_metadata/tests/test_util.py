from zion.util.get_url_metadata.util import (
    clean_url,
    convert_html_to_markdown,
    remove_html_tags,
)


def test_convert_html_to_markdown() -> None:
    # Test case 1: Empty HTML
    html_doc = ""
    expected_output = ""
    assert convert_html_to_markdown(html_doc) == expected_output

    # Test case 2: HTML with links
    html_doc = "<a href='https://example.com'>Example</a>"
    expected_output = "[Example](https://example.com)"
    assert convert_html_to_markdown(html_doc) == expected_output

    # Test case 3: HTML with bold text
    html_doc = "<b>Bold Text</b>"
    expected_output = "**Bold Text**"
    assert convert_html_to_markdown(html_doc) == expected_output

    # Test case 4: List conversion
    html_doc = "<ul><li>Item 1</li><li>Item 2</li></ul>"
    expected_output = "* Item 1\n* Item 2\n"
    assert convert_html_to_markdown(html_doc) == expected_output

    # Test case 5: Table conversion
    html_doc = "<table><tr><th>Header 1</th><th>Header 2</th></tr><tr><td>Data 1</td><td>Data 2</td></tr></table>"
    expected_output = "\n| Header 1 | Header 2 |\n| --- | --- |\n| Data 1 | Data 2 |\n"
    assert convert_html_to_markdown(html_doc) == expected_output


def test_remove_html_tags() -> None:
    # Test case 1: Empty HTML
    html_doc = ""
    expected_output = ""
    assert remove_html_tags(html_doc) == expected_output

    # Test case 2: HTML with tags to remove
    html_doc = "<script>Some script</script><nav>Navigation</nav><img src='image.jpg'>"
    expected_output = ""
    assert remove_html_tags(html_doc) == expected_output

    # Test case 3: HTML with no tags to remove
    html_doc = "<p>Some text</p>"
    expected_output = "<p>Some text</p>"
    assert remove_html_tags(html_doc) == expected_output

    # Test case 2: HTML with tags not in the list to remove
    html_doc = "<p>Some text</p><span>Span</span>"
    expected_output = "<p>Some text</p><span>Span</span>"
    assert remove_html_tags(html_doc) == expected_output

    # Test case 3: HTML with all tags to be removed except p tag
    html_doc = "<script></script><nav></nav><video></video><img src='image.jpg'><wbr></wbr><var></var><track></track><style></style><svg></svg><source></source><progress></progress><picture></picture><p>Some text</p>"
    expected_output = "<p>Some text</p>"
    assert remove_html_tags(html_doc) == expected_output


def test_clean_url() -> None:
    # Test case 1: Empty URL
    url = ""
    expected_output = ""
    assert clean_url(url) == expected_output

    # Test case 2: URL with query and fragment
    url = "https://example.com/page?param=value#section"
    expected_output = "https://example.com/page"
    assert clean_url(url) == expected_output

    # Test case 3: URL without query and fragment
    url = "https://example.com/page"
    expected_output = "https://example.com/page"
    assert clean_url(url) == expected_output

    # Test case 4: URL with only query
    url = "https://example.com/page?param=value"
    expected_output = "https://example.com/page"
    assert clean_url(url) == expected_output

    # Test case 5: URL with only fragment
    url = "https://example.com/page#section"
    expected_output = "https://example.com/page"
    assert clean_url(url) == expected_output
