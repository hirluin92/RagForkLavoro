from models.apis.document_intelligence_request_body import (
    DocumentIntelligenceRequestBody,
    ValueFromAzAISearch)
from models.apis.document_intelligence_response_body import (
    DataToAzAISearch,
    DocumentIntelligenceResponseBody, 
    ValueToAzAISearch)
from services.document_intelligence import a_analyze_layout
from services.logging import Logger


async def a_get_documents_content(req_body: DocumentIntelligenceRequestBody,
                        outputFormat: str,
                        logger: Logger) -> DocumentIntelligenceResponseBody:
    values = req_body.values
    results = DocumentIntelligenceResponseBody()
    for value in values:
        output_record = await a_get_content_from_document_intelligence(
            value,
            outputFormat,
            logger)
        results.addValue(output_record)

    return results

async def a_get_content_from_document_intelligence(value: ValueFromAzAISearch,
                                           outputFormat: str,
                                           logger: Logger) -> ValueToAzAISearch:
    recordId = value.recordId
    url_source = value.data.fileUrl + value.data.fileSasToken
    content_to_return = ""
    paragraphs_to_return = []
    tables_to_return = []
    try:
        content_from_document_intelligence = await a_analyze_layout(url_source, outputFormat)
        content_to_return = content_from_document_intelligence[0]
        paragraphs_to_return = content_from_document_intelligence[1]
        tables_to_return = content_from_document_intelligence[2]
        

        dataToReturn = DataToAzAISearch(content_to_return,
                                         paragraphs_to_return,
                                         tables_to_return)
        valueToReturn = ValueToAzAISearch(recordId, dataToReturn, None, None)
        return valueToReturn
    except Exception as error:
        error_message = "File processing error. File: {file} | Error: {error}"
        logger.exception(error_message.format(file=url_source, error=str(error)))
        return ValueToAzAISearch(recordId, {},
                                  [{ "message": "Error: " + str(error) }],
                                  None)