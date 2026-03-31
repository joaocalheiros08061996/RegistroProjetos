#connection.py
import os
import psycopg2


def get_connection():
    """
    Retorna uma conexão PostgreSQL com o Supabase.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL não definida")

    return psycopg2.connect(database_url)
