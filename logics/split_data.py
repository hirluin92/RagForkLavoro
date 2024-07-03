import azure.functions as func
from services.storage import a_upload_txt_to_blob, a_delete_blob_from_container
from utils.settings import get_storage_settings


def custom_chunking() -> list[str]:
    chunks = { "chunk1", "chunk2" }
    return chunks

async def a_split_data_into_chunks(myblob: func.InputStream) -> int: 
    storageSettings = get_storage_settings()
    dest_container = storageSettings.data_source_split_files_container
    blobNameList = myblob.name.split("/")
    filename = blobNameList[-1]
    source_container = blobNameList[0]
    blobNamePath = myblob.name.removeprefix(f"{source_container}/")
    blobfolderPath = blobNamePath.removesuffix(f"/{filename}")
    content = myblob.read().decode("utf-8")
    chunksList = content.split(sep="\r\n\r\n\r\n")
    for index, item in enumerate(chunksList):
        title = filename + f"_chunk{index+1}"
        blobPath = blobfolderPath + f"/{title}"
        await a_upload_txt_to_blob(dest_container, blobPath, item)
    tot = len(chunksList)
    await a_delete_blob_from_container(source_container, blobNamePath)
    return (tot, dest_container)
