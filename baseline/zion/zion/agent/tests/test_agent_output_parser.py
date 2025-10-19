from zion.agent.agent_output_parser import (
    parse_structured_response,
    structured_output_delimiter,
)


def test_parse_structured_response_happy_case() -> None:
    output, structured_output = parse_structured_response(
        """Testing

Content 1

Content 2

<-- structured_response_delimiter -->
```json
{
  "is_true": true,
  "sources": [{"name": "source1", "url": "url1"}, {"name": "source2", "url": "url2"}],
  "category": "query"
}
```"""
    )

    assert structured_output_delimiter not in output
    assert structured_output["is_true"] is True
    assert structured_output["category"] == "query"
    assert structured_output["sources"] == [
        {"name": "source1", "url": "url1"},
        {"name": "source2", "url": "url2"},
    ]


def test_parse_structured_response_with_additional_white_space() -> None:
    output, structured_output = parse_structured_response(
        """

Testing

Content 1

Content 2

<-- structured_response_delimiter -->


```json
{
  "is_true": true,
  "sources": [{"name": "source1", "url": "url1"}, {"name": "source2", "url": "url2"}],
  "category": "query"
}
```

"""
    )

    assert structured_output_delimiter not in output
    assert structured_output["is_true"] is True
    assert structured_output["category"] == "query"
    assert structured_output["sources"] == [
        {"name": "source1", "url": "url1"},
        {"name": "source2", "url": "url2"},
    ]


def test_parse_structured_response_with_invalid_code_block() -> None:
    output, structured_output = parse_structured_response(
        """

Testing

Content 1

Content 2

<-- structured_response_delimiter -->


!!!json
{
  "is_true": true,
  "sources": [{"name": "source1", "url": "url1"}, {"name": "source2", "url": "url2"}],
  "category": "query"
}
!!!

"""
    )

    assert structured_output_delimiter not in output
    assert structured_output == {}


def test_parse_structured_response_with_invalid_json() -> None:
    output, structured_output = parse_structured_response(
        """

Testing

Content 1

Content 2

<-- structured_response_delimiter -->


```json
{`is_true": true,
  "sources": [{"name": "source1", "url": "url1"}, {"name": "source2", "url": "url2"}],
  "category": "query"}
```

"""
    )

    assert structured_output_delimiter not in output
    assert structured_output == {}
