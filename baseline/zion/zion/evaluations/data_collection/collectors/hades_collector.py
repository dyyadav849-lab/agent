from datetime import datetime, timezone
from types import TracebackType
from typing import Optional

import httpx
from pydantic import ValidationError

from zion.config import global_config
from zion.evaluations.data_collection.collectors.base_collector import BaseCollector
from zion.evaluations.data_collection.models import EvaluationDataPoint
from zion.logger import get_logger

logger = get_logger(__name__)

# HTTP status codes
HTTP_OK = 200


class HadesCollector(BaseCollector):
    """Collector for Hades KB Service data"""

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.base_url = global_config.hades_kb_service_base_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url, timeout=float(config["hades"]["timeout"])
        )

    async def validate_connection(self) -> bool:
        """Validate connection to Hades KB Service"""
        try:
            response = await self.client.get("/health_check")
            is_valid = response.status_code == HTTP_OK
        except Exception:
            logger.exception("Failed to validate Hades connection")
            is_valid = False
        return is_valid

    async def collect_data(self) -> Optional[list[EvaluationDataPoint]]:
        """Collect data from Hades KB service.

        Collects messages based on channel IDs.
        """
        try:
            all_messages = []
            for channel_id in self.config["hades"]["channel_ids"]:
                messages = await self._fetch_messages(channel_id)
                if messages:
                    all_messages.extend(messages)

            if not all_messages:
                return None

            data_points = await self._process_messages(all_messages)
            if not data_points:
                return None

            try:
                self.update_last_collection_time(datetime.now(timezone.utc))
            except Exception:
                logger.exception("Failed to update collection time")
                return None
            else:
                return data_points

        except Exception:
            logger.exception("Failed to collect data from Hades KB")
            return None

    async def _fetch_messages(self, channel_id: str) -> Optional[list[dict]]:
        """Fetch messages from Hades KB service for a specific channel.

        Args:
            channel_id: The Slack channel ID to fetch messages from.

        Returns:
            Optional[list[dict]]: List of message dictionaries or None if fetch fails.
        """
        logger.info(
            "Collecting data from Hades KB",
            extra={
                "channel_id": channel_id,
            },
        )

        try:
            # Use the slack messages endpoint with configured parameters
            response = await self.client.get(
                "/slack/messages",
                params={
                    "channel_id": channel_id,
                },
            )

            # Log response details before raising status
            logger.info(
                "Received response from Hades KB",
                extra={
                    "status_code": response.status_code,
                    "response_headers": dict(response.headers),
                    "response_body": response.text[
                        :1000
                    ],  # Log first 1000 chars of response
                    "channel_id": channel_id,
                },
            )

            response.raise_for_status()

            # Parse and validate data
            data = response.json()
            if not isinstance(data, dict) or "messages" not in data:
                logger.error("Unexpected response format", extra={"data": data})
                return None

            return data["messages"]

        except Exception:
            logger.exception(
                "Failed to fetch messages from Hades KB",
                extra={"channel_id": channel_id},
            )
            return None

    async def _process_messages(
        self, messages: list[dict]
    ) -> list[EvaluationDataPoint]:
        """Process messages into evaluation data points.

        Args:
            messages: List of message dictionaries.

        Returns:
            list[EvaluationDataPoint]: List of processed data points.
        """
        data_points = []
        for msg in messages:
            # Extract only the required fields
            msg_data = {
                "id": msg.get("id"),
                "channel_id": msg.get("channel_id"),
                "main_thread_ts": msg.get("main_thread_ts"),
                "chat_summary": msg.get("chat_summary"),
                "chat_history": msg.get("chat_history", []),
            }

            try:
                data_point = await self._create_data_point(msg_data)
                if data_point:
                    data_points.append(data_point)
            except Exception:
                logger.exception(
                    "Failed to process message", extra={"msg_data": msg_data}
                )
                continue

        return data_points

    async def _create_data_point(self, msg_data: dict) -> Optional[EvaluationDataPoint]:
        """Create an EvaluationDataPoint from a message.

        Args:
            msg_data: Message dictionary.

        Returns:
            Optional[EvaluationDataPoint]: Created data point or None if invalid.
        """
        # Get user_id from first message in chat history
        user_id = "unknown"
        if msg_data["chat_history"] and isinstance(msg_data["chat_history"], list):
            first_msg = msg_data["chat_history"][0]
            if isinstance(first_msg, dict):
                # Extract user_id from message text (format: "username: message")
                msg_text = first_msg.get("text", "")
                if ":" in msg_text:
                    user_id = msg_text.split(":", 1)[0].strip()

        try:
            # Convert message to EvaluationDataPoint
            return EvaluationDataPoint(
                source="hades",
                input=None,  # No query for Hades
                user_id=user_id,
                main_thread_ts=msg_data["main_thread_ts"],
                channel_id=msg_data["channel_id"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                expected_output=msg_data["chat_summary"],
                tibot_id=0,
            )
        except (ValidationError, KeyError):
            logger.exception(
                "Failed to create data point", extra={"msg_data": msg_data}
            )
            return None

    async def __aenter__(self) -> "HadesCollector":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.client.aclose()
