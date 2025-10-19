import pytest

from app.core.s3.constant import FileType
from app.core.s3.file_util import (
    get_file_type,
    get_filename,
    get_media_mime_type,
    is_valid_file_upload_type,
)


class TestFileUtil:
    def test_is_valid_file_upload_type(self) -> None:
        test_cases = [
            {"file_name": "/example/test.txt", "is_valid": True},
            {"file_name": "/example/test.txt", "is_valid": True},
            {
                "file_name": "asdasdasd",  # invalid file name
                "is_valid": False,
            },
            {
                "file_name": "/example/test.webp",  # invalid file type
                "is_valid": False,
            },
        ]

        for test_case in test_cases:
            if test_case["is_valid"]:
                assert is_valid_file_upload_type(test_case["file_name"]) is None
            else:
                with pytest.raises(ValueError, match=r"Only .* files are supported"):
                    is_valid_file_upload_type(test_case["file_name"])

    def test_get_file_type(self) -> None:
        test_cases = [
            {"file_name": "/example/test.csv", "expected_output": FileType.CSV},
            {
                "file_name": "/example/asdasdsad",  # invalid filename
                "expected_output": ValueError(""),
            },
            {
                "file_name": "/example/test.webp",  # invalid filename
                "expected_output": ValueError(""),
            },
            {"file_name": "/example/test.docx", "expected_output": FileType.DOCX},
            {"file_name": "/example/test.xlsx", "expected_output": FileType.XLSX},
            {"file_name": "/example/test.xls", "expected_output": FileType.XLS},
            {"file_name": "/example/test.pdf", "expected_output": FileType.PDF},
        ]

        for test_case in test_cases:
            if isinstance(test_case["expected_output"], ValueError):
                with pytest.raises(ValueError, match=r"Only .* files are supported"):
                    is_valid_file_upload_type(test_case["file_name"])
            else:
                assert (
                    get_file_type(test_case["file_name"])
                    == test_case["expected_output"].value
                )

    def test_get_media_mime_type(self) -> None:
        test_cases = [
            {"file_name": "/example/test.csv", "meme_type": "text/csv"},
            {
                "file_name": "/example/test.docx",
                "meme_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            },
            {
                "file_name": "/example/test.xlsx",
                "meme_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            },
            {"file_name": "/example/test.xls", "meme_type": "application/vnd.ms-excel"},
            {"file_name": "/example/test.pdf", "meme_type": "application/pdf"},
            {"file_name": "/example/test.webp", "meme_type": "image/webp"},
        ]

        for test_case in test_cases:
            assert get_media_mime_type(test_case["file_name"]) == test_case["meme_type"]

    def test_get_filename(self) -> None:
        test_cases = [
            {"file_path": "/example/test.csv", "expected_output": "test.csv"},
            {"file_path": "/example/test.docx", "expected_output": "test.docx"},
            {"file_path": "/example/test.xlsx", "expected_output": "test.xlsx"},
            {"file_path": "/example/test.xls", "expected_output": "test.xls"},
            {"file_path": "/example/test.pdf", "expected_output": "test.pdf"},
            {"file_path": "/example/test.webp", "expected_output": "test.webp"},
        ]

        for test_case in test_cases:
            assert get_filename(test_case["file_path"]) == test_case["expected_output"]
