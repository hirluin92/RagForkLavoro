class RagOrchestratorResponse:
    def __init__(self, answer_text, llm_query_enriched, cqa_data, llm_data):
        self.answer_text = answer_text
        self.llm_query_enriched = llm_query_enriched
        self.cqa_data = cqa_data
        self.llm_data = llm_data