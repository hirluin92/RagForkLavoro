import json
import azure.functions as func
from models.apis.movefiles_request_body import MoveFilesRequestBody, ValueFromAzAISearch
from models.apis.movefiles_response_body import (
    ValueToAzAISearch
)
from services.logging import LoggerBuilder
import constants.event_types as event_types
from services.storage import get_blob_info_container_and_blobName, a_get_blob_stream_from_container
from models.apis.convert_docx_to_md_request_body import ConvertDocxToMdRequestBody
from models.apis.convert_docx_to_md_response_body import ConvertDocxToMdResponseBody, DataToAzAISearch
from services.storage import generate_blob_sas_from_blob_client, get_blob_client_from_blob_storage_path
import mammoth
from bs4 import BeautifulSoup

async def a_convert_docx_to_md(req_body: ConvertDocxToMdRequestBody,
                               context: func.Context) -> ConvertDocxToMdResponseBody:
    result = ConvertDocxToMdResponseBody()
    for value in req_body.values:
        moved_record = await a_convert_docx(value, context)
        result.addValue(moved_record)
    return result


async def a_convert_docx(item: ValueFromAzAISearch, context: func.Context) -> ValueToAzAISearch:
    with LoggerBuilder(__name__, context) as logger:
        blob_storage_path = item.data.fileUrl
        sas_token = item.data.fileSasToken
        source_url = blob_storage_path + sas_token
        if len(sas_token) == 0:
            blob_client = get_blob_client_from_blob_storage_path(
                blob_storage_path)
            sas_token = generate_blob_sas_from_blob_client(blob_client)
            source_url = blob_storage_path + "?" + sas_token
        blob_from_info = get_blob_info_container_and_blobName(source_url)
        blob_from_container = blob_from_info[0]
        blob_name = blob_from_info[1]
        try:
            with await a_get_blob_stream_from_container(blob_from_container, blob_name) as stream:
                finalText = extract_text_and_hyperlink(stream)
                return ValueToAzAISearch(item.recordId,
                                         DataToAzAISearch(finalText),
                                         None,
                                         None)
        except Exception as err:
            info_err = {"source_url": source_url, "Error": str(err)}
            logger.exception(str(err))
            logger.track_event(event_types.convert_docx_to_md_exception, info_err)
            data_error = [{"message": "Error: " + str(err)}]
            error_to_return = ValueToAzAISearch(
                item.recordId, {}, data_error, None)
            return error_to_return


def extract_text_and_hyperlink(stream: bytes) -> str:
    result = mammoth.convert_to_html(stream)
    htmlText = result.value
    soup = BeautifulSoup(htmlText, 'html.parser')
    hyperLinks = soup.find_all('a', href=True)
    for link in hyperLinks:
        text = link.text
        if not text:
            md_link = ""
        else:
            md_link = f"[{text}]({link['href']})"
        link.replace_with(md_link)       
    text = ""
    all_tags = soup.find_all()
    for tag in all_tags:
        text = text + " " + tag.get_text()
    return text
