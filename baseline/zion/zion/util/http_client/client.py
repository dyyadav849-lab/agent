from zion.config import global_config
from zion.util.http_client.base_class import HttpClient

# Base Url
hades_kb_service_url = global_config.hades_kb_service_base_url

# Singleton http client
hades_http_client = HttpClient(name="hades_kb_service", base_url=hades_kb_service_url)
