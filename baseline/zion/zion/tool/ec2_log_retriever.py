import re
import time
from typing import Any, Optional

from dateutil import parser
from langchain.callbacks.manager import (
    CallbackManagerForToolRun,
)
from langchain.tools import BaseTool
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from zion.config import logger
from zion.util.aws.aws import Attribute, Event, query_aws_cloudtrail
from zion.util.datadog.datadog import query_instance_id_from_instance_ip


class TimeRangeFilter(BaseModel):
    from_ts: str = Field(
        description='start time of the filter, return time in ISO8601 format (e.g. "2024-07-20T21:45:56.065340+08:00")'
    )
    to_ts: str = Field(
        description='end time of the filter, return time in ISO8601 format (e.g. "2024-07-20T21:45:56.065340+08:00"'
    )


class Ec2LogRetrieverInput(TimeRangeFilter):
    resource_name: str = Field(
        description="this is the resource name retrieved from user que"
    )
    resource_type: str = Field(
        description="this is the resource type, it could be one of ('AWS::EC2::Instance','AWS::ElasticLoadBalancing::LoadBalancer','AWS::AutoScaling::AutoScalingGroup','AWS::EC2::LaunchTemplate','AWS::DynamoDB::Table','AWS::AutoScaling::AutoScalingGroup')"
    )
    from_ts: str = Field(
        description='start time of the filter, return time in ISO8601 format (e.g. "2024-07-20T21:45:56.065340+08:00")'
    )
    to_ts: str = Field(
        description='end time of the filter, return time in ISO8601 format (e.g. "2024-07-20T21:45:56.065340+08:00"'
    )


class Ec2LogFilter(BaseModel):
    AttributeKey: str = Field("ResourceName or ResourceType")
    AttributeValue: str = Field("ResourceName or ResourceType value")


class Ec2LogRetrieverOutput(BaseModel):
    filters: list[Ec2LogFilter] = Field(
        description="this is the filter used to retrieve logs"
    )
    time_range: TimeRangeFilter = Field(
        description="this is the time range used to retrieve logs"
    )
    events: list[Event] = Field(
        description="this is the events retrieved from cloudtrail"
    )


class Ec2LogRetriever(BaseTool):
    name: str = "ec2_log_retriever"
    description: str = """
    This is a tool to retrieve logs from ec2 instance.
    """
    args_schema: type[BaseModel] = Ec2LogRetrieverInput
    handle_tool_error: bool = True  # handle ToolExceptions
    metadata: Optional[dict[str, Any]] = None

    def __init__(self) -> None:
        super().__init__()

    def _run(
        self,
        resource_name: str,
        resource_type: str,
        from_ts: str,
        to_ts: str,
        _: Optional[CallbackManagerForToolRun] = None,
    ) -> Ec2LogRetrieverOutput:
        return self.get_ec2_logs(resource_name, from_ts, to_ts, resource_type)

    def _arun(
        self,
        resource_name: str,
        resource_type: str,
        from_ts: str,
        to_ts: str,
        _: Optional[CallbackManagerForToolRun] = None,
    ) -> Ec2LogRetrieverOutput:
        return self.get_ec2_logs(resource_name, from_ts, to_ts, resource_type)

    def get_ec2_logs(
        self, resource_name: str, from_ts: str, to_ts: str, resource_type: str
    ) -> Ec2LogRetrieverOutput:
        try:
            instance_id = self.convert_to_instance_id(
                resource_name=resource_name,
                from_ts=from_ts,
                to_ts=to_ts,
            )

            cloud_trail_attributes = [
                Attribute(
                    AttributeKey="ResourceName",
                    AttributeValue=instance_id,
                ),
                Attribute(
                    AttributeKey="ResourceType",
                    AttributeValue=resource_type,
                ),
            ]
            return Ec2LogRetrieverOutput(
                filters=[
                    Ec2LogFilter(
                        AttributeKey="ResourceName",
                        AttributeValue=instance_id,
                    ),
                    Ec2LogFilter(
                        AttributeKey="ResourceType",
                        AttributeValue=resource_type,
                    ),
                ],
                time_range=TimeRangeFilter(from_ts=from_ts, to_ts=to_ts),
                events=query_aws_cloudtrail(
                    attributes=cloud_trail_attributes,
                    start_time=self.iso_timestamp(from_ts),
                    end_time=self.iso_timestamp(to_ts),
                ),
            )
        except Exception as e:
            err_message = f"Unable to retireve ec2 log with exception: {e!s}"
            logger.exception(err_message)
            raise ToolException(err_message) from e

    def convert_to_instance_id(
        self, resource_name: str, from_ts: str, to_ts: str
    ) -> str:
        """convert ec2 ip to instance id"""
        rs = re.findall(
            r"\b(?:[1-2]?[0-9]{1,2}\.){3}[1-2]?[0-9]{1,2}\b",
            resource_name.replace("-", "."),
        )
        if rs:
            # get instance id from datadog with instance ip
            return query_instance_id_from_instance_ip(
                rs[0], self.iso_timestamp(from_ts), self.iso_timestamp(to_ts)
            )
        # no ip found, response origin value
        return resource_name

    def iso_timestamp(self, iso_time: str) -> int:
        date = parser.parse(iso_time)
        timestamp = time.mktime(date.timetuple())
        return int(timestamp)
