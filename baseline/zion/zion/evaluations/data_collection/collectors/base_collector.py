from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from zion.evaluations.data_collection.models import EvaluationDataPoint


class BaseCollector(ABC):
    """Base class for all data collectors"""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.last_collection_time: Optional[datetime] = None

    @abstractmethod
    async def collect_data(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> list[EvaluationDataPoint]:
        """Collect data from the source

        Args:
            start_time: Optional start time for data collection
            end_time: Optional end time for data collection

        Returns:
            List of EvaluationDataPoint objects
        """

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate connection to the data source

        Returns:
            True if connection is valid, False otherwise
        """

    def update_last_collection_time(self, time: datetime) -> None:
        """Update the last collection time

        Args:
            time: The time of the last successful collection
        """
        self.last_collection_time = time
