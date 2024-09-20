import aioodbc

from models.services.mssql_tag import MsSqlTag
from utils.settings import get_mssql_settings

async def a_get_tags_by_tag_names(tag_names: list[str]) -> list[MsSqlTag]:
    settings = get_mssql_settings()
    tags_filter = ",".join(["'" + str(x) + "'" for x in tag_names])
    sql_query = f"""
    SELECT [Name]
    ,[Description]
    FROM [dbo].[Tags]
    WHERE [Name] IN ({tags_filter})
    """ 
    tags_to_return: list[MsSqlTag] = []
    async with aioodbc.create_pool(dsn=settings.connection_string) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql_query)
                records = await cursor.fetchall()
                for r in records:
                    tags_to_return.append(MsSqlTag(r.Name, r.Description))

    return tags_to_return