from datadog import api, initialize

from zion.config import global_config

prefix_tag = "log_digger."
elapsed_tag = ".elapsed"
count_tag = ".count"


initialize(
    statsd_socket_path=global_config.dd_statsd_socket_path,
    api_key=global_config.datadog_api_key,
    app_key=global_config.datadog_app_key,
)


def query_instance_id_from_instance_ip(
    instance_ip: str, from_ts: int, to_ts: int
) -> str:
    rs = api.Metric.query(
        start=from_ts,
        end=to_ts,
        query=f"sum:aws.ec2.host_ok{{ host:*{instance_ip} }} by {{instance_id,host}}",
    )
    if rs.get("status", {}) == "ok":
        ids = [
            tag.split(":")[1]
            for series in rs["series"]
            for tag in series["tag_set"]
            if "instance_id:" in tag
        ]
        if ids:
            return ids[0]
    return instance_ip
