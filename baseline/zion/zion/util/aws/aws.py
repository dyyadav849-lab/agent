import json
from datetime import datetime
from typing import NamedTuple

import boto3
import pytz
from aws_assume_role_lib import assume_role
from botocore.config import Config
from dateutil.parser import parse
from pydantic import BaseModel, Field

from zion.config import global_config, logger
from zion.util.aws.constant import (
    CLOUDTAIL_URL_PREFIX,
    CLOUDTRAIL_ASSUME_ROLE_MAIN_ACCOUNT,
    CLOUDTRAIL_RESPONSE_LIMIT,
    DEFAULT_AWS_REGION,
    DEFAULT_TIMEZONE_REGION,
)


class Attribute(NamedTuple):
    AttributeKey: str
    AttributeValue: str


class Event(BaseModel):
    """
    A class used to represent an AWS CloudTrail Event
    """

    event_id: str = Field(description="The unique identifier for the event")
    event_name: str = Field(description="The name of the event")
    event_time: str = Field(description="The time the event occurred")
    username: str = Field(description="The name of the user who initiated the event")
    link: str = Field(description="The cloud trail link of the event")


def remove_tz_suffix(dt_str: str) -> str:
    # 2024-07-18 10:42:19+00:00 -> 2024-07-18 10:42:19
    # 2024-07-18 10:42:19+08:00 -> 2024-07-18 10:42:19
    return dt_str.replace("+08:00", "").replace("+00:00", "")


# NOTE: AWS returns the time in UTC+8 in local, but UTC+0 in STG/ PRD
# This function is used to make sure the convertion is correct for all.
# AWS time format: 2024-07-18 10:45:26+00:00
def convert_from_aws_time_to_sgt(time_str: str) -> str:
    # Parse string to datetime
    dt = parse(time_str)

    # Convert to Singapore time
    return dt.astimezone(pytz.timezone(DEFAULT_TIMEZONE_REGION))


def get_cloudtrail_readonly_role_main_account() -> boto3.Session.client:
    if global_config.environment == "dev":
        return boto3.Session().client("cloudtrail", region_name=DEFAULT_AWS_REGION)

    assume_session = assume_role(boto3.Session(), CLOUDTRAIL_ASSUME_ROLE_MAIN_ACCOUNT)

    return assume_session.client(
        "cloudtrail",
        config=Config(
            region_name=DEFAULT_AWS_REGION,
            retries={"max_attempts": 5, "mode": "standard"},
        ),
    )


cloudtrail_readonly_role_main_account = get_cloudtrail_readonly_role_main_account()


def query_aws_cloudtrail(
    attributes: list[Attribute], start_time: datetime, end_time: datetime
) -> list[Event]:
    logger.info(
        f"Querying CloudTrail for {start_time} to {end_time} with attributes {attributes}"
    )
    resource_name = next(
        (
            item.AttributeValue
            for item in attributes
            if item.AttributeKey == "ResourceName"
        ),
        None,
    )
    if resource_name is None:
        return []
    # Match the resource name and resource type
    target_name = ""
    target_type = ""
    target_event_name = ""
    for item in attributes:
        if item.AttributeKey == "ResourceName":
            target_name = item.AttributeValue
            continue
        if item.AttributeKey == "ResourceType":
            target_type = item.AttributeValue
            continue
        if item.AttributeKey == "EventName":
            target_event_name = item.AttributeValue
    result = []

    for event in lookup_events(resource_name, start_time, end_time):
        event_name = event["EventName"]
        if target_event_name not in ("", event_name):
            continue
        trail_event_str = event["CloudTrailEvent"]
        cloud_trail_event_dict = json.loads(trail_event_str)
        resources = event["Resources"]

        valid = False
        # Now you can access the values in the dictionary like so:
        if target_name in f"{cloud_trail_event_dict['requestParameters']}":
            valid = any(
                is_valid_resource(resource, target_type, target_name)
                for resource in resources
            )
        if valid:
            event_time_str = str(event["EventTime"])
            event_sgt_time = convert_from_aws_time_to_sgt(event_time_str)
            event_sgt_time_without_tz = remove_tz_suffix(str(event_sgt_time))
            result.append(
                Event(
                    event_id=event["EventId"],
                    event_name=event["EventName"],
                    event_time=event_sgt_time_without_tz,
                    username=extract_user_name(cloud_trail_event_dict)
                    or event.get("UserName"),
                    link=f"{CLOUDTAIL_URL_PREFIX}?EventId={event['EventId']}",
                )
            )
    return result[:CLOUDTRAIL_RESPONSE_LIMIT]


def extract_user_name(event: dict) -> str:
    arn_val = event.get("userIdentity", {}).get("arn", "")
    return "/".join(arn_val.split("/")[-2:])


def is_valid_resource(resource: dict, target_type: str, target_name: str) -> bool:
    resource_type = resource.get("ResourceType")
    return (resource_type is None or resource_type == target_type) and resource[
        "ResourceName"
    ] == target_name


def lookup_events(resource: str, start: datetime, end: datetime) -> list:
    response = cloudtrail_readonly_role_main_account.lookup_events(
        LookupAttributes=[
            {
                "AttributeKey": "ResourceName",
                "AttributeValue": resource,
            }
        ],
        StartTime=start,
        EndTime=end,
    )

    events = response["Events"]

    while "NextToken" in response:
        response = cloudtrail_readonly_role_main_account.lookup_events(
            LookupAttributes=[
                {
                    "AttributeKey": "ResourceName",
                    "AttributeValue": resource,
                }
            ],
            StartTime=start,
            EndTime=end,
            NextToken=response["NextToken"],
        )
        events.extend(response["Events"])

    return events
