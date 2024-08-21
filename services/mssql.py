import pyodbc

from models.services.mssql_tag import MsSqlTag
from utils.settings import get_mssql_settings

def get_connection_string():
    settings = get_mssql_settings()
    conn = pyodbc.connect(settings.connection_string)

    return conn

def get_tags_by_tag_names(tag_names: list[str]) -> list[MsSqlTag]:
    conn = get_connection_string()
    tags_filter = ",".join(["'" + str(x) + "'" for x in tag_names])
    sql_query = f"""
    SELECT [Name]
    ,[Description]
    FROM [dbo].[Tags]
    WHERE [Name] IN ({tags_filter})
    """ 
    cursor = conn.cursor()
    cursor.execute(sql_query)
    records = cursor.fetchall()
    tags_to_return: list[MsSqlTag] = []
    for r in records:
        tags_to_return.append(MsSqlTag(r.Name, r.Description))

    return tags_to_return