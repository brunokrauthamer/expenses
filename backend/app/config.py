import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def get_database_url() -> str:
    """Retorna a URL do PostgreSQL configurada para a aplicação."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "A variável DATABASE_URL não foi definida. "
            "Copie .env.example para .env e informe a conexão com o PostgreSQL."
        )
    return database_url
