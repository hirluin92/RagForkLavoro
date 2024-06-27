from functools import cache
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from tenacity import retry, stop_after_attempt, wait_exponential
from utils.settings import get_document_intelligence_settings

@cache
def get_document_intelligence_client(endpoint, key) -> DocumentIntelligenceClient:
    document_intelligence_client = DocumentIntelligenceClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )
    return document_intelligence_client

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(3),
    reraise=True
)
async def a_analyze_layout(url_source: str,
        outputFormat: str | None) -> tuple[str, list, list]:
    settings = get_document_intelligence_settings()
    document_intelligence_client = get_document_intelligence_client(settings.endpoint,
                                                                        settings.key)
    poller = await document_intelligence_client.begin_analyze_document(
        "prebuilt-layout", 
        AnalyzeDocumentRequest(url_source=url_source),
        output_content_format=outputFormat)

    result: AnalyzeResult = await poller.result()

    contentToReturn = result.content

    paragraphsToReturn = []
    if result.paragraphs:
        for paragraph in result.paragraphs:
            paragraphsToReturn.append(
                {
                    "role": paragraph.role,
                    "content": paragraph.content
                }
            )

    tablesToReturn = []
    if result.tables:
        for table in result.tables:
            cellsToReturn = []
            for cell in table.cells:
                cellsToReturn.append(
                                {
                                    "content": cell.content,
                                    "rowIndex": cell.row_index,
                                    "colIndex": cell.column_index,
                                    "kind": cell.kind
                                }
                            )
            tablesToReturn.append(
                            {
                                "row_count": table.row_count,
                                "column_count": table.column_count,
                                "cells": cellsToReturn
                            }
                        )
    return (contentToReturn, paragraphsToReturn, tablesToReturn)