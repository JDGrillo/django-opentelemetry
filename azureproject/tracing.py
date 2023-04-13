import logging
import os
from dotenv import load_dotenv

from opentelemetry import trace
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from azure.monitor.opentelemetry import configure_azure_monitor


def request_hook(span, request):
    pass
    # print("TESTING request_hook")


def response_hook(span, request, response):
    pass
    # print("TESTING response_hook")


def log_hook(span, record):
    pass
    # print("LOOG HOOK")


def instrument_app():
    provider = TracerProvider()
    trace.set_tracer_provider(provider)

    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

    # from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

    # exporter = AzureMonitorTraceExporter(
    #     connection_string=appKey
    # )

    # from azure.monitor.opentelemetry.exporter import AzureMonitorMetricExporter
    # exporter = AzureMonitorMetricExporter(
    #     connection_string=appKey
    # )

    # from azure.monitor.opentelemetry.exporter import AzureMonitorLogExporter
    # exporter = AzureMonitorLogExporter(
    #     connection_string=appKey
    # )

    DjangoInstrumentor().instrument(tracer_provider=provider, is_sql_commentor_enabled=True, request_hook=request_hook, response_hook=response_hook)
    LoggingInstrumentor().instrument(tracer_provider=provider, log_hook=log_hook)
    Psycopg2Instrumentor().instrument(tracer_provider=provider, skip_dep_check=True, enable_commenter=True)
    RequestsInstrumentor().instrument(tracer_provider=provider)