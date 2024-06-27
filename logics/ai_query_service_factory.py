import services
import services.ai_query_service_mistralai
import services.ai_query_service_openai
from logics.ai_query_service_base import AiQueryServiceBase 


class AiQueryServiceFactory:
    @staticmethod
    def get_instance(model_id: str) -> AiQueryServiceBase:

        model_id = model_id.upper()

        if model_id == services.ai_query_service_openai.AiQueryServiceOpenAI.model_id():
            return services.ai_query_service_openai.AiQueryServiceOpenAI()
        
        if model_id == services.ai_query_service_mistralai.AiQueryServiceMistralAI.model_id():
            return services.ai_query_service_mistralai.AiQueryServiceMistralAI()

        # Gestore di default        
        return services.ai_query_service_openai.AiQueryServiceOpenAI()
    