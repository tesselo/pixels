import os

from sqlalchemy import create_engine


def create_db_engine_pxsearch():
    """
    Create database engine from environment variables to Pxsearch Db.
    """
    pg_user = os.environ.get("DB_USER_PXSEARCH", "postgres")
    pg_pass = os.environ.get("DB_PASS_PXSEARCH", "")
    pg_host = os.environ.get("DB_HOST_PXSEARCH", "localhost")
    pg_port = os.environ.get("DB_PORT_PXSEARCH", "5432")
    pg_dbname = os.environ.get("DB_NAME_PXSEARCH", "pxsearch")
    db_url = f"postgresql+pg8000://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_dbname}"

    return create_engine(db_url, client_encoding="utf8")
