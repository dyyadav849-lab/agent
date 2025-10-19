from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


def generate_slack_link(channel_id: str, thread_ts: str) -> str:
    """Generate a Slack link for a given channel and thread timestamp.

    Args:
        channel_id: The Slack channel ID
        thread_ts: The thread timestamp (main_thread_ts)

    Returns:
        str: The formatted Slack URL
    """
    url_format = "https://grab.slack.com/archives/<CHANNEL_ID>/p<main_thread_ts>"
    return url_format.replace("<CHANNEL_ID>", str(channel_id)).replace(
        "<main_thread_ts>", str(thread_ts)
    )


class SlackMessageInfo(BaseModel):
    """Model for slack_message_information table data from Hades KB Service"""

    message_id: str
    channel_id: str
    user_id: str
    message_text: str
    thread_ts: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: dict = Field(default_factory=dict)


class LevelZeroEnquiry(BaseModel):
    """Model for level_zero_enquiries table data from TI Support Bot"""

    enquiry_id: str
    user_id: str
    channel_id: str
    message_text: str
    response_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: dict = Field(default_factory=dict)


class EvaluationDataPoint(BaseModel):
    """Combined model for evaluation data points"""

    source: str  # 'hades' or 'ti-support'
    input: Optional[str] = None
    expected_output: Optional[str] = None
    created_at: datetime
    main_thread_ts: Optional[str] = None
    threaded_message_id: Optional[str] = None
    chat_summary: Optional[str] = None
    chat_history_count: Optional[int] = None
    updated_at: Optional[datetime] = None
    channel_id: str
    channel_name: Optional[str] = None
    slack_url: Optional[str] = None
    # TI Support specific fields
    query_category: Optional[str] = None
    can_be_answered: Optional[bool] = None
    is_in_hades: Optional[bool] = None

    def to_langsmith_example(self) -> dict:
        """Convert to LangsmithTestExample format"""
        metadata = {
            "test_case_name": f"{self.channel_name}",
            "test_case_description": f"{self.query_category}",
            "source": self.source,
            "main_thread_ts": self.main_thread_ts,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "slack_url": self.slack_url,
            "created_at": self.created_at.isoformat(),
            "chat_summary": self.chat_summary,
            "chat_history_count": self.chat_history_count,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "query_category": self.query_category,
            "can_be_answered": self.can_be_answered,
            "is_in_hades": self.is_in_hades,
        }
        return {
            "metadata": metadata,
            "inputs": {
                "input": self.input,
                "channel_name": self.channel_name,
                "slack_url": self.slack_url,
            },
            "outputs": {"expected_output": self.expected_output},
        }
