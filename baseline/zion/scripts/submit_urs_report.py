import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests
from dateutil.tz import tzutc
from defusedxml import ElementTree as DefusedET
from tzlocal import get_localzone

coverage_file_path = Path.cwd() / "coverage.xml"
junit_file_path = Path.cwd() / "junit.xml"
coverage_type = "code_coverage"
urs_base_url = "https://urs.stg-myteksi.com"
urs_api_submit_report = f"{urs_base_url}/urs/v1/report"
urs_api_submit_coverage = f"{urs_base_url}/urs/v1/coverage"


def get_coverage() -> list[dict]:
    xml_tree = parse_xml(coverage_file_path)
    root = xml_tree.getroot()
    result = []

    result.append(
        {
            "name": "Zion Code Coverage",
            "coverage_type": coverage_type,
            "covered": int(root.attrib["lines-covered"]),
            "total": int(root.attrib["lines-valid"]),
            "value": float(root.attrib["line-rate"]),
        }
    )

    return result


def parse_xml(file_path: str) -> ET.ElementTree:
    return DefusedET.parse(file_path)


def convert_time_to_millis(timestamp_str: str) -> int:
    """Convert timestamp format 2024-09-25T14:14:59.395455+08:00 to milliseconds"""
    dt_object = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    return int(dt_object.timestamp() * 1000)


def convert_milliseconds_to_time_str(millseconds: int) -> int:
    """Convert millesconds back to timestamp format 2024-04-29T16:55:22.200199"""
    dt_object = datetime.fromtimestamp(millseconds / 1000, get_localzone())
    return dt_object.strftime("%Y-%m-%dT%H:%M:%S.%f")


def convert_to_urs_time_format(timestamp_str: str) -> str:
    """Convert timestamp format 2024-09-25T14:14:59.395455+08:00 to 2024-04-29T08:55:22.20019900Z, SG time to UTC"""
    dt_object_sgt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    dt_object_utc = dt_object_sgt.astimezone(tzutc())
    return dt_object_utc.strftime("%Y-%m-%dT%H:%M:%S.%f00Z")


def get_test_report() -> dict:
    xml_tree = parse_xml(junit_file_path)
    root = xml_tree.getroot()

    test_suites = []
    start_time = ""
    end_time = ""

    for i, suite in enumerate(root.findall("testsuite")):
        timestamp_in_mills = convert_time_to_millis(suite.attrib["timestamp"])

        if i == 0:
            start_time = suite.attrib["timestamp"]
            end_time = suite.attrib["timestamp"]

        suite_timestamp = (
            float(suite.attrib["time"]) * 1000
        )  # convert seconds to milliseconds
        suite_end_time = suite_timestamp + timestamp_in_mills

        if suite_end_time > float(timestamp_in_mills):
            end_time = convert_milliseconds_to_time_str(suite_end_time)

        test_cases = []

        for test_case in suite.findall("test_case"):
            status = "passed"
            if test_case.findall("failure"):
                status = "failed"
            elif test_case.findall("error"):
                status = "error"
            elif test_case.findall("skipped"):
                status = "skipped"
            test_cases.append(
                {
                    "name": test_case.attrib["name"],
                    "time": float(test_case.attrib["time"]),
                    "status": status,
                }
            )

        suite_status = "passed"
        if int(suite.attrib["failures"]) > 0:
            suite_status = "failed"

        test_suites.append(
            {
                "name": suite.attrib["name"],
                "time": float(suite.attrib["time"]),
                "status": suite_status,
                "test_cases": test_cases,
            }
        )

    return {
        "test_suites": test_suites,
        "start_time": convert_to_urs_time_format(start_time),
        "end_time": convert_to_urs_time_format(end_time),
    }


def send_coverage_data_to_urs(test_run_id: str) -> None:
    suite_coverages = get_coverage()

    json_payload = {
        "service_name": "zion",
        "tech_family": "foundations",
        "report_type": "unit_test",
        "platform": "backend",
        "branch_name": "master",
        "criticality": "useful",
        "test_run_id": int(test_run_id),
        "coverages": [
            {
                "coverage_type": coverage_type,
                "covered": suite_coverages[0]["covered"],
                "total": suite_coverages[0]["total"],
            },
        ],
        "suite_coverages": suite_coverages,
    }

    res = requests.post(
        urs_api_submit_coverage,
        data=json.dumps(json_payload),
        headers={
            "Content-Type": "application/json",
        },
        timeout=10,
    )

    if res.status_code != requests.codes.no_content:
        print("Failed to send coverage data to URS")  # noqa: T201
        return

    print("Success! Coverage data sent to URS")  # noqa: T201


def send_test_report_to_urs() -> dict[str, str]:
    test_report = get_test_report()

    json_payload = {
        "service_name": "zion",
        "tech_family_name": "foundations",
        "report_type": "unit_test",
        "platform": "backend",
        "branch_name": "master",
        "criticality": "useful",
        "start_time": test_report["start_time"],
        "end_time": test_report["end_time"],
        "test_suites": test_report["test_suites"],
    }

    res = requests.post(
        urs_api_submit_report,
        data=json.dumps(json_payload),
        headers={
            "Content-Type": "application/json",
        },
        timeout=10,
    )

    if res.status_code != requests.codes.ok:
        print("Failed to send test report data to URS")  # noqa: T201
        return None

    print("Success! Test Report data sent to URS")  # noqa: T201

    return res.json()


if __name__ == "__main__":
    report_res_data = send_test_report_to_urs()
    send_coverage_data_to_urs(report_res_data["test_run_id"])
