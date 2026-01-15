from services.logging import Logger

from aioodbc import create_pool
from models.apis.rag_orchestrator_request import PromptEditorCredential
from models.services.mssql_tag import MsSqlTag
from utils.settings import get_mssql_settings


async def a_get_tags_by_tag_names(logger: Logger, tag_names: list[str]) -> list[MsSqlTag]:
    settings = get_mssql_settings()
    tags_filter = ",".join(["'" + str(x) + "'" for x in tag_names])
    sql_query = f"""
    SELECT [Name]
    ,[Description]
    ,[EnableCQA]
    ,[EnableEnrichment]
    ,[IdMonitoringQuestion]
    FROM [dbo].[Tags]
    WHERE [Name] IN ({tags_filter})
    """
    tags_to_return: list[MsSqlTag] = []
    logger.info(f"before a_get_tags_by_tag_names")
    try:
        async with create_pool(dsn=settings.connection_string, minsize=1) as pool:
            async with pool.acquire() as conn:
                logger.info(f"connection established")
                async with conn.cursor() as cursor:
                    await cursor.execute(sql_query)
                    records = await cursor.fetchall()
                    for r in records:
                        tags_to_return.append(MsSqlTag(
                        r.Name, 
                        r.Description, 
                        r.EnableCQA,
                        r.EnableEnrichment,
                        r.IdMonitoringQuestion))

            logger.info(f"after a_get_tags_by_tag_names")
            return tags_to_return
    except Exception as ex:
        logger.exception(ex)
        raise ex

async def a_get_prompt_info(logger: Logger, tag_name: str, type_filters: list[str], llm_id: str) -> list[PromptEditorCredential]:
    logger.info("before a_get_prompt_info")
    settings = get_mssql_settings()
    try:
        async with create_pool(dsn=settings.connection_string, minsize=1) as pool:
            async with pool.acquire() as conn:
                logger.info("connection established")
                async with conn.cursor() as cursor:
                    # Trasmormo l'array in una lista di valori separati da rigola
                    type_filters_str = ','.join(f"{type_}" for type_ in type_filters)
                    
                    sql_query = f"""
                    WITH FilteredRows AS (
                        SELECT 
                            PromptDetails.ID,
                            PromptId,
                            PromptVersion,
                            PromptType,
                            TagName,
                            ROW_NUMBER() OVER (
                                PARTITION BY PromptType 
                                ORDER BY CASE 
                                    WHEN TagName = ? THEN 1 
                                    WHEN TagName IS NULL THEN 2 
                                    ELSE 3
                                END
                            ) AS RowNum
                        FROM PromptDetails JOIN
                        Llms ON PromptDetails.LlmId = Llms.Id
                        WHERE PromptType IN (SELECT value FROM STRING_SPLIT('{type_filters_str}', ','))
                        AND Llms.Code = ?
                    )
                    SELECT 
                        PromptId, PromptVersion, PromptType
                    FROM 
                        FilteredRows
                    WHERE 
                        RowNum = 1;
                    """
                    
                    # Eseguo...
                    await cursor.execute(sql_query, tag_name, llm_id)
                    
                    # Itera sui risultati e costruisce la lista da restituire
                    prompt_version_infos = []
                    async for record in cursor:
                        prompt_version_infos.append(
                            PromptEditorCredential(
                                id=record.PromptId,
                                version=record.PromptVersion,
                                type=record.PromptType,
                            )
                        )
                    
                    logger.info("after a_get_prompt_info")
                    return prompt_version_infos
    except Exception as ex:
        logger.exception(ex)
        raise ex

async def a_check_status_tag_for_mst(logger: Logger, tag_name: str, status: bool) -> bool:
    settings = get_mssql_settings()
    sql_query = f"""
    SELECT IdMonitoringQuestion
    FROM [dbo].[Tags]
    WHERE [Name] = '{tag_name}'
    """
    logger.info(f"before a_check_status_tag_for_mst")
    try:
        async with create_pool(dsn=settings.connection_string, minsize=1) as pool:
            async with pool.acquire() as conn:
                    logger.info(f"connection established")
                    async with conn.cursor() as cursor:
                        await cursor.execute(sql_query)
                        records = await cursor.fetchall()
                        logger.info(f"after a_check_status_tag_for_mst")
                        return len(records) > 0
    except Exception as ex:
        logger.exception(ex)
        raise ex    