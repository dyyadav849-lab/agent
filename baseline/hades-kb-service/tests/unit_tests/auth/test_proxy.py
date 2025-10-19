from unittest import TestCase

from fastapi import Request
from starlette.datastructures import Headers

from app.auth.proxy import get_credentials_via_proxy


class TestProxy(TestCase):
    def test_get_credentials_via_proxy(self) -> None:
        dummy_credentials = "Bearer <token>"

        headers = {
            "Authorization": dummy_credentials,
        }
        dummy_request = Request(
            {
                "type": "http",
                "headers": Headers(headers).raw,
            }
        )
        got = get_credentials_via_proxy(dummy_request)
        assert got == dummy_credentials
