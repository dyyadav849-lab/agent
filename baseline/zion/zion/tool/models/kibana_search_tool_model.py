from typing import Optional


class KibanaLogRecord:
    def __init__(
        self, url: str = "", message: str = "", additional_data: str = ""
    ) -> None:
        self.url = url
        self.message = message
        self.additional_data = additional_data

    def __repr__(self) -> str:
        return f"KibanaLogRecord(URL: {self.url}, Message={self.message}), Additional Data: {self.additional_data}"


class KibanaLogRecordAggregated:
    def __init__(
        self,
        url: str = "",
        message: str = "",
        additional_data: str = "",
        occurences: int = 0,
        request_ids: Optional[list] = None,
    ) -> None:
        self.url = url
        self.message = message
        self.additional_data = additional_data
        self.occurences = occurences
        self.request_ids = request_ids

    def __repr__(self) -> str:
        return f"""
        KibanaLogRecordAggregated(URL: {self.url}, Message={self.message}), Additional Data: {self.additional_data}, Request IDs: {self.request_ids} Occurences: {self.occurences})
        """
