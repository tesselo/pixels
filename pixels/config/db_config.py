import os

from sqlalchemy import create_engine


# editar nomes de variaveis de ambiente da maquina da aws de acordo com o que esta lá configurado para cada um
def create_connection_pixels():
    """
    Get connection URL from environment variables to to Pixels DB.
    """
    pg_user = os.environ.get("DB_USER_PIXELS", "postgres")
    pg_pass = os.environ.get("DB_PASS_PIXELS", "")
    pg_host = os.environ.get("DB_HOST_PIXELS", "localhost")
    pg_port = os.environ.get("DB_PORT_PIXELS", "5432")
    pg_dbname = os.environ.get("DB_NAME_PIXELS", "pixels")
    db_url = f"postgresql+pg8000://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_dbname}"

    return create_engine(db_url, client_encoding="utf8")


def create_connection_pxsearch():
    """
    Get connection URL from environment variables to Pxsearch Db.
    """
    pg_user = os.environ.get("DB_USER_PXSEARCH", "postgres")
    pg_pass = os.environ.get("DB_PASS_PXSEARCH", "")
    pg_host = os.environ.get("DB_HOST_PXSEARCH", "localhost")
    pg_port = os.environ.get("DB_PORT_PXSEARCH", "5432")
    pg_dbname = os.environ.get("DB_NAME_PXSEARCH", "prod")
    db_url = f"postgresql+pg8000://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_dbname}"

    return create_engine(db_url, client_encoding="utf8")
