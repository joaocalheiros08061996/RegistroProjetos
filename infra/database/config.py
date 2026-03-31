#config.py
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para o ambiente
load_dotenv()

# URL de conexão com o PostgreSQL (Supabase)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL não encontrada. Verifique se o arquivo .env existe "
        "e se contém a variável DATABASE_URL."
    )
