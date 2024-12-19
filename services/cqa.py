from functools import cache
import json
from logging import Logger
from azure.core.credentials import AzureKeyCredential
from azure.ai.language.questionanswering.aio import QuestionAnsweringClient
from constants import event_types, environment
from models.configurations.cqa import CQASettings
from models.services.cqa_response import CQAResponse
from services.storage import a_get_blob_content_from_container
 
@cache
def get_question_answering_client(key_credential: str,
                                  endpoint: str):
    credential = AzureKeyCredential(key_credential)
    client = QuestionAnsweringClient(endpoint, credential)
    return client

async def a_do_query(query: str, topic:str, logger: Logger)-> CQAResponse:
    """
    Questa funzione esegue una query di domanda e risposta utilizzando il servizio di Azure QnA Maker.
    Prende in input una domanda e restituisce la risposta ottenuta dal servizio.
    Restituisce None se non riesce a contattare il servizio oppure se non riesce a dare una risposta
    """    
    settings = CQASettings()
    
    try:
        client = get_question_answering_client(settings.key_credential,
                                               settings.endpoint)
        
        project_name, deployment_name = await a_get_cqa_project_by_topic(settings.config_container, topic=topic, logger=logger)

        if project_name is None:
            logger.error(f"No project found for topic '{topic}' in CQA Mapping")
            return None

        output = await client.get_answers(
            question=query,
            project_name=project_name,
            deployment_name=deployment_name,
            ranker_kind="QuestionOnly"
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
    

async def a_get_cqa_project_by_topic(container_name: str,topic:str, logger: Logger)-> tuple:
    file_content = await a_get_blob_content_from_container(container_name, environment.TAGS_MAPPING)
    maps = json.loads(file_content)
    for elemento in maps:
        if elemento["ai_service"] == topic:
            return elemento["cqa_project"], elemento["cqa_deployment"]
    
    logger.warning(f"Topic '{topic}' not found in CQA mapping")
    return None, None  