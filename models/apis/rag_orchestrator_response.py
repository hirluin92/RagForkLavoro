class RagOrchestratorResponse:
    def __init__(self, answer_text, llm_query_enriched, cqa_data, llm_data, monitor_form_application = None):
        self.answer_text = answer_text
        self.llm_query_enriched = llm_query_enriched
        self.cqa_data = cqa_data
        self.llm_data = llm_data
        self.monitor_form_application = monitor_form_application

class EventMonitorFormApplication:
    user_not_authenticated = "UserNotAuthenticated"
    user_no_form_application = "UserNoFormApplication"
    show_answer_text = "ShowAnswerText"
    show_answer_list = "ShowAnswerList"


class MonitorFormApplication:
    def __init__(self, answer_text = None, answer_list = None, event_type = None):
        self.answer_text = answer_text
        self.answer_list = answer_list
        self.event_type = event_type
    answer_text: str
    answer_list: str
    event_type: EventMonitorFormApplication