import os

DEBUG = os.environ.get('DEBUG', False)
SQLALCHEMY_DATABASE_URI = os.environ.get(
    'SQLALCHEMY_DATABASE_URI',
    'postgresql://postgres:postgres@localhost/tesselo',
)
SQLALCHEMY_TRACK_MODIFICATIONS = False
