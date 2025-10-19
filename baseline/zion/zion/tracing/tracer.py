import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as OTLPGRPCSpanExporter,
)
from opentelemetry.sdk.resources import (
    CONTAINER_IMAGE_NAME,
    CONTAINER_IMAGE_TAG,
    KUBERNETES_NAMESPACE_NAME,
    KUBERNETES_POD_NAME,
    SERVICE_NAME,
    SERVICE_VERSION,
    Resource,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)

from zion.config import global_config, logger

KUBERNETES_NODE_NAME = "k8s.node.name"
KUBERNETES_POD_IP = "k8s.pod.ip"
KUBERNETES_APP_INSTANCE = "k8s.app.instance"
PLATFORM_NAME = "platform_name"

ENV_POD_NAME = "POD_NAME"
ENV_POD_NAMESPACE = "POD_NAMESPACE"
ENV_POD_NODE_NAME = "POD_NODE_NAME"
ENV_POD_IP = "POD_IP"
ENV_APP_INSTANCE = "APP_INSTANCE"
ENV_CONTAINER_IMAGE = "CONTAINER_IMAGE"
ENV_PLATFORM_NAME = "PLATFORM_NAME"
ENV_APP_NAME = "APP_NAME"

CONTAINER_IMAGE_SEP = ":"
EXPECTED_IMAGE_INFO_LEN = 2

OTEL_SCHEMA_URL = "https://opentelemetry.io/schemas/1.21.0"

# derive container image info, in expected form <IMAGE_NAME>:<IMAGE_TAG>
container_image_fullname = str(os.environ.get(ENV_CONTAINER_IMAGE))
container_image_info = container_image_fullname.split(CONTAINER_IMAGE_SEP, 1)
container_image_name = container_image_info[0]
container_image_tag = "unknown"
if len(container_image_info) == EXPECTED_IMAGE_INFO_LEN:
    container_image_tag = container_image_info[1]


otel_resource = Resource.create(
    attributes={
        SERVICE_NAME: os.environ.get(ENV_APP_NAME),
        SERVICE_VERSION: container_image_tag,
        KUBERNETES_NAMESPACE_NAME: os.environ.get(ENV_POD_NAMESPACE),
        KUBERNETES_POD_NAME: os.environ.get(ENV_POD_NAME),
        KUBERNETES_NODE_NAME: os.environ.get(ENV_POD_NODE_NAME),
        KUBERNETES_POD_IP: os.environ.get(ENV_POD_IP),
        KUBERNETES_APP_INSTANCE: os.environ.get(ENV_APP_INSTANCE),
        CONTAINER_IMAGE_NAME: container_image_name,
        CONTAINER_IMAGE_TAG: container_image_tag,
        PLATFORM_NAME: os.environ.get(ENV_PLATFORM_NAME),
    },
    schema_url=OTEL_SCHEMA_URL,
)

trace.set_tracer_provider(TracerProvider(resource=otel_resource))
tracer = trace.get_tracer(f"llmkit.{os.environ.get(ENV_APP_NAME)}")

# replace processor with ConsoleSpanExporter for trace-debugging in dev
# for stg/prd use the OTLPSpanExporter
processor = OTLPGRPCSpanExporter(endpoint=global_config.otel_exporter_otlp_endpoint)
logger.info(f"spans will be sent to {global_config.otel_exporter_otlp_endpoint}")

trace_provider = trace.get_tracer_provider()
trace_provider.add_span_processor(BatchSpanProcessor(processor))
