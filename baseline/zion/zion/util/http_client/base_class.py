from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Optional

import requests
from requests import RequestException, Session
from requests.adapters import HTTPAdapter

from zion.config import logger


class HttpClient:
    def __init__(self, name: str, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests.Session()
        self.__logger = logger
        self.__name = name

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager to provide a session and ensure proper cleanup.
        """
        try:
            # Create an HTTPAdapter object and configure connection pooling and retries
            adapter = HTTPAdapter(pool_connections=20, pool_maxsize=5, max_retries=3)

            # Mount the HTTPAdpater object to the session
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)
            yield self.session
        except ConnectionError as e:
            error_message = f"Hades kb service client error: {e!s}"
            self.__logger.exception(error_message)
        except RequestException as e:
            res_body_text = f"http request failed: {e!s}"
            self.__logger.exception(res_body_text)
            raise RequestException(res_body_text) from e
        finally:
            self.session.close()

    def get(
        self,
        session: Session,
        endpoint: str = "",
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        **kwargs: dict[str, Any],
    ) -> dict:
        """
        Perform a GET request using the provided session.
        """
        if headers:
            kwargs.setdefault("headers", {}).update(headers)

        response = session.get(f"{self.base_url}{endpoint}", params=params, **kwargs)
        response.raise_for_status()  # Raise an exception for 4xx/5xx responses if any
        return response.json()

    def post(
        self,
        session: Session,
        endpoint: str = "",
        data: Optional[dict] = None,
        json: Optional[dict] = None,
        headers: Optional[dict] = None,
        **kwargs: dict[str, Any],
    ) -> dict | None:
        """
        Perform a POST request using the provided session.
        """
        if headers:
            kwargs.setdefault("headers", {}).update(headers)

        response = session.post(
            f"{self.base_url}{endpoint}", data=data, json=json, **kwargs
        )
        response.raise_for_status()  # Raise an exception for 4xx/5xx responses if any
        return response.json()
