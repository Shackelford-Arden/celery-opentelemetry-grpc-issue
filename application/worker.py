import sys

import requests
from celery import Celery
from celery.signals import worker_process_init
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import set_span_in_context
from opentelemetry.trace import SpanKind

from application.utils.celery_utils import AppTask


@worker_process_init.connect(weak=False)
def init_celery_tracing(*args, **kwargs):  # pylint: disable=unused-argument

    provider = TracerProvider()
    if 'pytest' in sys.modules:
        exporter = InMemorySpanExporter()
    else:
        exporter = OTLPSpanExporter()

    trace.set_tracer_provider(provider)
    span_processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(span_processor=span_processor)

    trace.get_tracer_provider().add_span_processor(
        span_processor=span_processor
    )


capp = Celery("capp", broker='redis://issue-redis:6379', backend='redis://issue-redis:6379', task_cls=AppTask)


@capp.task(bind=True)
def my_task(self: AppTask):
    """
    Generate a bunch of spans really quickly within the context of a Celery
    task.
    """

    with self.tracer.start_span('Parent Span', kind=SpanKind.INTERNAL) as parent_span:
        parent_context = set_span_in_context(parent_span)

        for item in range(1000):
            with self.tracer.start_span('Child Span', context=parent_context):
                print("Hello!")
                requests.get('http://api:8080/api/status')


if __name__ == "__main__":
    capp.worker_main()
