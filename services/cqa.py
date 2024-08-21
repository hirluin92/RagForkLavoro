from functools import cache
import json
from logging import Logger
from azure.core.credentials import AzureKeyCredential
from azure.ai.language.questionanswering.aio import QuestionAnsweringClient
from constants import event_types
from models.configurations.cqa import CQASettings
from models.services.cqa_response import CQAResponse

@cache
def get_question_answering_client(key_credential: str,
                                  endpoint: str):
    credential = AzureKeyCredential(key_credential)
    client = QuestionAnsweringClient(endpoint, credential)
    return client

async def a_do_query(query: str, logger: Logger)-> CQAResponse:
    """
    Questa funzione esegue una query di domanda e risposta utilizzando il servizio di Azure QnA Maker.
    Prende in input una domanda e restituisce la risposta ottenuta dal servizio.
    Restituisce None se non riesce a contattare il servizio oppure se non riesce a dare una risposta
    """    
    settings = CQASettings()
    try:
        client = get_question_answering_client(settings.key_credential,
                                               settings.endpoint)
        project_name = settings.knowledgebase_project 
        
        output = await client.get_answers(
            question=query,
            project_name=project_name,
            deployment_name=settings.deployment
        )

        logger.track_event(event_types.cqa_answer_event,
                       {"question": query,
                        "answer": json.dumps(output.serialize())})
        
        # Verifico se la risposta è accettabile
        if not output.answers[0] or output.answers[0].answer == str(settings.default_noresult_answer):
            return None
        
        if output.answers[0].confidence < float(settings.confidence_threshold):
            return None
        
        text_response = str(output.answers[0].answer)

        # Rimuovo la proprietà answer perchè è duplicata
        del output.answers[0].answer
        
        return CQAResponse(text_response,output.answers[0])
    except Exception as e:
        print("Error executing CQA query:", str(e))
        raise