import json, os, psycopg2

def read_file(file_name: str, *path: list[str | int]):
    with open(file_name, "r") as file:
        position = json.load(file)
    for key in path:
        if key is None:
            return None
        position = position.get(str(key), None)
    return position

def read_sql(table_name: str, guild_id: int, column_name: str):
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url, sslmode="require")
    exists_query = f"SELECT EXISTS(SELECT 1 FROM {table_name} WHERE guild_id = {guild_id})";
    query = f"SELECT {column_name} FROM {table_name} WHERE guild_id = {guild_id};"
    cursor = conn.cursor()

    cursor.execute(exists_query)
    if cursor.fetchall() == []:
        return None
    cursor.execute(query)

    results = cursor.fetchall()
    results = results[0][0]
    cursor.close()
    conn.close()
    return results

def write_sql(table_name: str, guild_id: int, column_name: str, value: any):
    database_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(database_url, sslmode="require")
    query = f"INSERT INTO {table_name} (guild_id, {column_name}) VALUES ({guild_id}, {value}) ON CONFLICT (guild_id) DO UPDATE SET {column_name}={value};"
    cursor = conn.cursor()
    cursor.execute(query)

    conn.commit()
    cursor.close()
    conn.close()