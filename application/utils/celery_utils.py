import functools

from celery import Task
from celery.utils.log import get_task_logger
from opentelemetry import propagate
from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.propagate import extract
from opentelemetry.sdk.trace import Span
from opentelemetry.sdk.trace import Tracer
from opentelemetry.trace import format_trace_id
from opentelemetry.trace import set_span_in_context
from opentelemetry.trace import SpanKind


class AppTask(Task):
    # OpenTelemetry Attributes
    _tracer: Tracer = None
    _context = None
    _current_span = None
    _parent_context = None
    _context_headers = {}
    _propogate = propagate.get_global_textmap()
    _logger = get_task_logger(__name__)

    trace_id = None

    def log(self, msg: str):
        self._logger.info(msg=msg, extra={'props': {'trace_id': self.trace_id, 'correlation_id': self.trace_id}})

    def log_error(self, msg: str):
        self._logger.error(msg=msg, extra={'props': {'trace_id': self.trace_id, 'correlation_id': self.trace_id}})

    @property
    def tracer(self) -> Tracer:
        if self._tracer is None:
            self._tracer = trace.get_tracer(__name__)
        return self._tracer

    @property
    def context(self):
        self._context = extract(self.request.kwargs.get('otel', {}))
        return self._context

    @property
    def current_span(self):
        return self._current_span

    @current_span.setter
    def current_span(self, current_span: Span):
        self._current_span = current_span

    @property
    def parent_context(self):
        return self._parent_context

    @parent_context.setter
    def parent_context(self, task_context: Context):
        self._parent_context = task_context

    @property
    def context_headers(self):
        # Pass this along when wanting to show task as parent
        return self._context_headers

    @property
    def propogate(self):
        return self._propogate


def otel_wrapper(func):
    @functools.wraps(func)
    def generate_span(*args, **kwargs):
        task = None

        try:
            task = args[0]
        except IndexError:
            pass

        with task.tracer.start_span(task.name, context=task.context, kind=SpanKind.CONSUMER) as span:
            task.current_span = span
            task.parent_context = set_span_in_context(span)
            task.trace_id = format_trace_id(trace_id=span.get_span_context().trace_id)

            # This will allow a task to use the self.context_headers variable
            # to continue to inherit from the previous parent without the
            # hassle of putting the headers together
            task.propogate.inject(task.context_headers, task.parent_context)

            # For now going to remove otel argument so that it does not carry
            # to the task and cause pylint issues as it is not needed in the
            # actual task itself. Is it the right thing to do? Only time will
            # tell and am torn if this is the right approach.
            try:
                del kwargs['otel']
            except KeyError:
                pass

            try:
                results = func(*args, **kwargs)
            except Exception as task_error:
                span.record_exception(task_error)
                raise task_error

        return results

    return generate_span
