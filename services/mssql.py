from logging import Logger
import aioodbc

from models.services.mssql_tag import MsSqlTag, PromptVersionInfo
from utils.settings import get_mssql_settings

async def a_get_tags_by_tag_names(logger: Logger, tag_names: list[str]) -> list[MsSqlTag]:
    settings = get_mssql_settings()
    tags_filter = ",".join(["'" + str(x) + "'" for x in tag_names])
    sql_query = f"""
    SELECT [Name]
    ,[Description]
    FROM [dbo].[Tags]
    WHERE [Name] IN ({tags_filter})
    """ 
    tags_to_return: list[MsSqlTag] = []
    logger.info(f"before a_get_tags_by_tag_names")
    async with aioodbc.create_pool(dsn=settings.connection_string) as pool:
        async with pool.acquire() as conn:
            logger.info(f"connection established")
            async with conn.cursor() as cursor:
                await cursor.execute(sql_query)
                records = await cursor.fetchall()
                for r in records:
                    tags_to_return.append(MsSqlTag(r.Name, r.Description))

    logger.info(f"after a_get_tags_by_tag_names")
    return tags_to_return


async def a_get_prompt_info(logger: Logger, tag_name: str, type_filters: list[str]) -> list[PromptVersionInfo]:
    settings = get_mssql_settings()
    logger.info("before a_get_prompt_info")
    
    try:
        async with aioodbc.create_pool(dsn=settings.connection_string) as pool:
            async with pool.acquire() as conn:
                logger.info("connection established")
                async with conn.cursor() as cursor:
                    # Trasmormo l'array in una lista di valori separati da rigola
                    type_filters_str = ','.join(f"'{type_}'" for type_ in type_filters)
                    
                    sql_query = f"""
                    WITH FilteredRows AS (
                        SELECT 
                            ID,
                            IdPrompt,
                            IdVersion,
                            Type,
                            Tag,
                            ROW_NUMBER() OVER (
                                PARTITION BY Type 
                                ORDER BY CASE 
                                    WHEN Tag IS NOT NULL AND Tag = ? THEN 1 
                                    ELSE 2 
                                END
                            ) AS RowNum
                        FROM YourTable
                        WHERE Type IN (SELECT value FROM STRING_SPLIT({type_filters_str}, ','))
                    )
                    SELECT 
                        IdPrompt, IdVersion, Type
                    FROM 
                        FilteredRows
                    WHERE 
                        RowNum = 1;
                    """
                    
                    # Eseguo...
                    await cursor.execute(sql_query, (tag_name,))
                    
                    # Itera sui risultati e costruisce la lista da restituire
                    prompt_version_infos = []
                    async for record in cursor:
                        prompt_version_infos.append(
                            PromptVersionInfo(
                                id=record.IdPrompt,
                                version=record.IdVersion,
                                type=record.Type,
                            )
                        )
                    
                    logger.info("after a_get_prompt_info")
                    return prompt_version_infos

    except Exception as e:
        logger.error(f"Error in a_get_prompt_info: {e}")
        return []
