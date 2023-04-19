from opentelemetry import trace
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor


def instrument_app():

    DjangoInstrumentor().instrument(is_sql_commentor_enabled=True)
    LoggingInstrumentor().instrument()
    Psycopg2Instrumentor().instrument(skip_dep_check=True, enable_commenter=True)
    RequestsInstrumentor().instrument()