import logging
import os

from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource


def setup_logging(service_name: str | None = None):
    """Ship application logs to the OTel Collector, which forwards them to Loki.

    Attaches an OTLP logging handler to the root logger so every log record is
    exported over OTLP alongside traces (correlated by service.name / trace id).
    """
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
    service_name = service_name or os.getenv("OTEL_SERVICE_NAME", "api-gateway")

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = LoggerProvider(resource=resource)
    provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint, insecure=True))
    )
    set_logger_provider(provider)

    handler = LoggingHandler(level=logging.INFO, logger_provider=provider)
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
