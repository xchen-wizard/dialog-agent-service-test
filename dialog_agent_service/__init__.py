from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime

import flask
import mysql.connector.pooling
import pymongo
from dotenv import load_dotenv
from gql import Client
from gql import gql
from gql.transport.requests import RequestsHTTPTransport
from pythonjsonlogger import jsonlogger


load_dotenv(os.getenv('ENV_FILE') or '.env')

logger = logging.getLogger(__name__)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def __init__(self, fmt: str, extras: dict = None):
        super().__init__(fmt)
        self.extras = extras

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            # this doesn't use record.created, so it is slightly off
            now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
        if log_record.get('severity'):
            log_record['severity'] = log_record['level'].upper()
        else:
            log_record['severity'] = record.levelname
        if self.extras is not None:
            for key, value in self.extras.items():
                log_record[key] = value


def init_mysql_db():
    """
    Instantiate a mysql connector pool
    """
    if os.getenv('UNITTEST') and os.getenv('UNITTEST').lower() == 'true':
        return
    mysql_config = {
        'user': os.getenv('MYSQL_USER'),
        'password': os.getenv('MYSQL_PASSWORD'),
        'host': os.getenv('MYSQL_HOST'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'database': os.getenv('MYSQL_DATABASE'),
        'pool_name': 'mysqlpool',
        # 32 max_connections for the local mysql db
        'pool_size': int(os.getenv('MYSQL_POOL_SIZE', 32)),
        'autocommit': True,
    }

    # explicitly creating a connection pool
    for _ in range(3):  # num of retries
        try:
            mysql_pool = mysql.connector.pooling.MySQLConnectionPool(
                **mysql_config,
            )
            return mysql_pool
        except mysql.connector.Error as err:
            logger.error(f'prolbem initializing mysql connector pool: {err}')
            time.sleep(3)  # sleep for 3 secs
    raise Exception('mySQL connection error!')


def init_mongo_db():
    """
    Instantiate a mongo connector (thread-safe)
    """
    if os.getenv('UNITTEST') and os.getenv('UNITTEST').lower() == 'true':
        return
    # MongoDB connectors
    mongo_url: str = os.getenv('MONGODB_URL')
    mongo_db = pymongo.MongoClient(mongo_url)[os.getenv('MONGODB_DBNAME')]
    return mongo_db


def create_app():
    # create and configure the app
    app = flask.Flask(__name__)
    app.config['DEBUG'] = os.getenv('LOG_LEVEL') == 'DEBUG'
    return app


def init_logger():
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'info').upper()
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(LOG_LEVEL)
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(severity)s %(filename)s %(funcName)s %(lineno)s %(message)s',
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    return formatter


def init_gql():
    if os.getenv('UNITTEST') and os.getenv('UNITTEST').lower() == 'true':
        return
    access_token = get_gql_access_token()
    if not access_token:
        raise Exception('We cannot get the access token!')
    headers = {
        'Authorization': f"Bearer {access_token['merchantUserLogin']['accessToken']}",
    }
    transport = RequestsHTTPTransport(
        url=os.getenv('GQL_ENDPOINT'),
        use_json=True,
        headers=headers,
    )
    # Create a GraphQL client using the defined transport
    client = Client(transport=transport, fetch_schema_from_transport=True)
    return client


def get_gql_access_token():
    transport = RequestsHTTPTransport(
        url=os.getenv('GQL_ENDPOINT'),
        use_json=True,
        verify=True,
        retries=3,
    )
    client = Client(transport=transport, fetch_schema_from_transport=True)
    query = gql("""
    mutation MerchantUserLogin($input: MerchantUserLoginInput) {
      merchantUserLogin(input: $input) {
        accessToken
      }
    }
    """)
    vars = {
        'input': {
            'password': os.getenv('GQL_API_APP_SECRET'),
            'userName': os.getenv('GQL_USER'),
        },
    }
    resp = client.execute(document=query, variable_values=vars)
    return resp
