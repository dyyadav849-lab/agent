from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup
from markdownify import markdownify


def remove_html_tags(html_doc: str) -> str:
    """Removes specific html tags from the html code"""
    tags_to_remove = [
        "script",
        "nav",
        "video",
        "img",
        "wbr",
        "var",
        "track",
        "style",
        "svg",
        "source",
        "progress",
        "picture",
    ]
    html_doc_soup = BeautifulSoup(html_doc, "html.parser")
    for tag in tags_to_remove:
        for match in html_doc_soup.find_all(tag):
            match.decompose()

    return str(html_doc_soup)


def clean_url(url: str) -> str:
    """
    Clean the URL by removing the query and fragment
    """
    parsed_url = urlparse(url)
    clean_url = parsed_url._replace(query="", fragment="")
    return urlunparse(clean_url)


def convert_html_to_markdown(html_doc: str) -> str:
    """
    Convert HTML to markdown
    Refer: https://pypi.org/project/markdownify/
    """
    markdown_doc = markdownify(html_doc)

    # remove extra new lines
    for _ in range(5):
        markdown_doc = markdown_doc.replace("\n\n", "\n")
    return markdown_doc
