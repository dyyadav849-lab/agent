import prestodb

from zion.config import global_config


def query_presto(presto_sql: str) -> list[str]:
    """Allows user to query presto based on given presto sql"""
    conn = prestodb.dbapi.connect(
        host="porta.data-engineering.myteksi.net",
        port=443,
        http_scheme="https",
        auth=prestodb.auth.BasicAuthentication(
            f"{global_config.presto_username};cloud=aws&mode=adhoc",
            global_config.presto_password,
        ),
        catalog="hive",
        schema="public",
    )
    cur = conn.cursor()
    cur.execute(presto_sql)
    return cur.fetchall()
