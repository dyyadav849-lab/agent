from datetime import datetime, timezone
from types import TracebackType
from typing import Optional

import httpx

from zion.config import global_config
from zion.evaluations.data_collection.collectors.base_collector import BaseCollector
from zion.evaluations.data_collection.models import (
    EvaluationDataPoint,
)
from zion.logger import get_logger

logger = get_logger(__name__)

# HTTP status codes
HTTP_OK = 200


class TISupportCollector(BaseCollector):
    """Collector for TI Support Bot data"""

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.base_url = global_config.ti_support_base_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url, timeout=float(config["ti_support"]["timeout"])
        )

    async def validate_connection(self) -> bool:
        """Validate connection to TI Support Bot"""
        # If required comment health_check validation and return True when testing locally
        try:
            response = await self.client.get("/health_check")
            is_valid = response.status_code == HTTP_OK
        except Exception:
            logger.exception("Failed to validate TI Support connection")
            is_valid = False
        return is_valid

    async def collect_data(self, last_n_days: int = 1) -> list[EvaluationDataPoint]:
        """Collect data from TI Support

        Args:
            last_n_days: Number of days to look back. Defaults to 1 if not specified.
                        Can be overridden by config value if available.

        Returns:
            list[EvaluationDataPoint]: List of data points collected from TI Support.
        """
        try:
            # Override with config value if available
            if "last_n_days" in self.config["ti_support"]:
                last_n_days = self.config["ti_support"]["last_n_days"]

            # Get topics data
            topics = await self._fetch_topics(last_n_days)
            if not topics:
                return None

            data_points = await self._process_topics(topics)
            if not data_points:
                return None

            try:
                logger.info(
                    "Successfully processed topics from TI Support",
                    extra={"count": len(data_points)},
                )
            except Exception:
                logger.exception("Failed to log success message")
                return None
            else:
                return data_points

        except Exception:
            logger.exception("Failed to collect data from TI Support")
            return None

    async def _fetch_topics(self, last_n_days: int) -> list[dict]:
        """Fetch topics from TI Support API.

        Args:
            last_n_days: Number of days to look back.

        Returns:
            list[dict]: List of topic dictionaries.
        """
        topic_config = self.config["ti_support"]["topic_collection"]
        data = await self.get_topics(
            l0_query_categories=topic_config["query_categories"],
            l0_can_be_answered=topic_config["can_be_answered"],
            l0_channel_ids=topic_config["channel_ids"],
            l0_is_in_hades=topic_config["is_in_hades"],
            l0_agent_types="TI Bot Agent,TI Bot Multi-Agent,cloud-infra-agent,TI On-Call Multi-Agent",
            last_n_days=last_n_days,
        )

        # Validate response
        if not isinstance(data, dict) or "results" not in data:
            logger.error(
                "Invalid response format from TI Support API", extra={"data": data}
            )
            return []

        # Get topics list from the response
        results = data["results"]
        if isinstance(results, list):
            # If results is directly a list, use it as topics
            topics = results
        elif isinstance(results, dict):
            # If results is a dict, try to get topics from it
            topics = results.get("topics", [])
        else:
            logger.error(
                "Unexpected results type",
                extra={"type": type(results), "results": results},
            )
            return []

        if not isinstance(topics, list):
            logger.error(
                "Expected topics to be a list",
                extra={"type": type(topics), "topics": topics},
            )
            return []

        logger.info("Received topics from TI Support", extra={"count": len(topics)})
        return topics

    async def _process_topics(self, topics: list[dict]) -> list[EvaluationDataPoint]:
        """Process topics into evaluation data points.

        Args:
            topics: List of topic dictionaries.

        Returns:
            list[EvaluationDataPoint]: List of processed data points.
        """
        data_points = []
        for topic in topics:
            if not isinstance(topic, dict):
                logger.warning("Skipping non-dict topic", extra={"topic": topic})
                continue

            try:
                data_point = await self._create_data_point(topic)
                if data_point:
                    data_points.append(data_point)
            except Exception:
                logger.exception("Error processing topic", extra={"topic": topic})
                continue

        return data_points

    async def _get_channel_name(self, channel_id: str) -> Optional[str]:
        """Get channel name from TI Support Bot API.

        Args:
            channel_id: The Slack channel ID.

        Returns:
            Optional[str]: Channel name if found, None otherwise.
        """
        try:
            logger.info(
                "Fetching channel name",
                extra={
                    "channel_id": channel_id,
                    "endpoint": "/tisupportbot/slack-channel",
                },
            )
            response = await self.client.get(
                "/tisupportbot/slack-channel", params={"channel_id": channel_id}
            )
            logger.info(
                "Channel name API response",
                extra={
                    "channel_id": channel_id,
                    "status_code": response.status_code,
                    "response_text": response.text,
                },
            )
            if response.status_code == HTTP_OK:
                data = response.json()
                if data.get("slackChannels"):
                    for channel in data["slackChannels"]:
                        if channel["channel_id"] == channel_id:
                            channel_name = channel["channel_name"]
                            logger.info(
                                "Retrieved channel name",
                                extra={
                                    "channel_id": channel_id,
                                    "channel_name": channel_name,
                                },
                            )
                            return channel_name
        except Exception:
            logger.exception(
                "Failed to fetch channel name", extra={"channel_id": channel_id}
            )
        return None

    async def _create_data_point(self, topic: dict) -> Optional[EvaluationDataPoint]:
        """Create an EvaluationDataPoint from a topic.

        Args:
            topic: Topic dictionary.

        Returns:
            Optional[EvaluationDataPoint]: Created data point or None if invalid.
        """
        # Extract required fields (mapping API response fields to expected names)
        channel_id = topic.get("channelID")
        thread_ts = topic.get("threadTs")
        query = topic.get("query")
        query_category = topic.get("queryCategory")
        enquiry_id = topic.get("enquiryID")
        user_id = topic.get("slackUserID")
        threaded_message_ts = topic.get("threadedMessageTs")

        # Get channel name
        channel_name = None
        if channel_id:
            channel_name = await self._get_channel_name(channel_id)

        # For created_at, use thread timestamp as fallback since API doesn't provide explicit created_at
        created_at = None
        if thread_ts:
            try:
                created_at_dt = datetime.fromtimestamp(
                    float(thread_ts), tz=timezone.utc
                )
                created_at = created_at_dt.isoformat()
            except (ValueError, TypeError):
                pass

        # Validate required fields
        if not all(
            [
                channel_id,
                thread_ts,
                query,
                query_category,
                enquiry_id,
                user_id,
                created_at,
            ]
        ):
            logger.warning(
                "Skipping topic with missing required fields", extra={"topic": topic}
            )
            return None

        try:
            created_at_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError as e:
            logger.warning(
                "Invalid created_at date format",
                extra={"created_at": created_at, "error": str(e)},
            )
            return None

        # Create data point
        return EvaluationDataPoint(
            source="ti_support",
            channel_id=channel_id,
            channel_name=channel_name,
            main_thread_ts=thread_ts,
            input=query,  # Use query as input
            created_at=created_at_dt,
            query_category=query_category,
            expected_output=topic.get(
                "chat_summary", ""
            ),  # Uses chat_summary as expected_output
            can_be_answered=topic.get("canBeAnswered") == "Yes",
            is_in_hades=topic.get("isInHades") is True,
            threaded_message_id=threaded_message_ts,
        )

    async def get_topics(  # noqa: PLR0913
        self,
        l0_query_categories: Optional[str] = None,
        l0_can_be_answered: Optional[str] = None,
        l0_channel_ids: Optional[str] = None,
        l0_is_in_hades: Optional[str] = None,
        l0_agent_types: Optional[str] = None,
        last_n_days: Optional[int] = None,
    ) -> dict:
        """Get topics from TI Support Bot

        Args:
            l0_query_categories: Comma-separated list of query categories (e.g. "Others,Issue")
            l0_can_be_answered: Filter by whether query can be answered (e.g. "Yes")
            l0_channel_ids: Comma-separated list of channel IDs (e.g. "C08PVAV980M")
            l0_is_in_hades: Filter by whether query is in Hades (e.g. "true")
            l0_agent_types: Comma-separated list of agent types (e.g. "cloud-infra-agent,TI Bot Agent")
            last_n_days: Number of days to look back for topics

        Returns:
            Dictionary containing the topics data
        """
        try:
            # Build query parameters
            params = {}
            if l0_query_categories:
                params["l0_query_categories"] = l0_query_categories
            if l0_can_be_answered:
                params["l0_can_be_answered"] = l0_can_be_answered
            if l0_channel_ids:
                params["l0_channel_ids"] = l0_channel_ids
            if l0_is_in_hades:
                params["l0_is_in_hades"] = l0_is_in_hades
            if l0_agent_types:
                params["l0_agent_types"] = l0_agent_types
            if last_n_days is not None:
                params["l0_last_n_days"] = last_n_days

            # Fetch data from API
            response = await self.client.get(
                "/tisupportbot/ti-support/level-zero-enquiries", params=params
            )
            response.raise_for_status()

            return response.json()

        except httpx.HTTPError:
            logger.exception("HTTP error while fetching topics")
            raise
        except Exception:
            logger.exception("Unexpected error while fetching topics")
            raise

    async def __aenter__(self) -> "TISupportCollector":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.client.aclose()
