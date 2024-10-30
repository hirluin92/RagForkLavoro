import json
from logging import getLogger
import azure.functions as func
# from azure.monitor.events.extension import track_event

# from opentelemetry.context import attach, detach
# from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


class LoggerBuilder:
    def __init__(self, name: str, context: func.Context):
        self.name = name
        self.context = context

    def __enter__(self):
        # functions_current_context = {
        #     "traceparent": self.context.trace_context.Traceparent,
        #     "tracestate": self.context.trace_context.Tracestate
        # }
        # parent_context = TraceContextTextMapPropagator().extract(
        #     carrier=functions_current_context
        # )
        # self.token = attach(parent_context)
        # return Logger(self.name, self.context.invocation_id, self.context.trace_context.Traceparent.split('-')[1])
        return Logger(self.name, "nd", "nd")

    def __exit__(self, *args):
        # detach(self.token)
        pass


class Logger:
    def __init__(self, name: str, invocation_id: str, operation_id: str):
        self.logger = getLogger(name)
        self.invocation_id = invocation_id
        self.operation_id = operation_id

    def info(self, message):
        self.logger.info("INFO: " + message,
                         extra={"InvocationId": self.invocation_id})

    def warning(self, message):
        self.logger.warning(
            "WARN: " + message, extra={"InvocationId": self.invocation_id})

    def error(self, message):
        self.logger.error("ERROR: " + message,
                          extra={"InvocationId": self.invocation_id})

    def exception(self, message):
        self.logger.exception(
            "EXCEPTION: " + message, extra={"InvocationId": self.invocation_id})

    def track_event(self, event_name: str, properties: dict):
        properties.update({"InvocationId": self.invocation_id})
        self.logger.info("CUSTOM EVENT: " + event_name + " " + json.dumps(properties),
                         extra={"InvocationId": self.invocation_id})

    def get_operation_id(self):
        return self.operation_id

    def get_invocation_id(self):
        return self.invocation_id
