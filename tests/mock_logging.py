from services.logging import LoggerBuilder


class MockLogger:
    def info(self, message):
        pass

    def warning(self, message):
        pass

    def exception(self, message):
        pass

    def track_event(self, event_name: str, properties: dict):
        pass

class MockLoggerBuilder:
    def __enter__(self):
        return MockLogger()
    
    def __exit__(self, *args):
        pass

def set_mock_logger_builder(mocker):
    mocker.patch.object(LoggerBuilder,
                        "__new__",
                        return_value = MockLoggerBuilder())