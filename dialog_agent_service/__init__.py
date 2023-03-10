import flask
import logging
import os
import sys

import mysql.connector.pooling
import pymongo

from datetime import datetime
from pythonjsonlogger import jsonlogger

from dotenv import load_dotenv

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
        'pool_size': int(os.getenv('MYSQL_POOL_SIZE', 32)),  # 32 max_connections for the local mysql db
        'autocommit': True,
    }

    # Attempt initial connection to make sure we can connect
    try:
      cnx = mysql.connector.connect(user=os.getenv('MYSQL_USER'), 
                                    password=os.getenv('MYSQL_PASSWORD'), 
                                    host=os.getenv('MYSQL_HOST'), 
                                    port=int(os.getenv('MYSQL_PORT', 3306)),
                                    database=os.getenv('MYSQL_DATABASE'))
    except mysql.connector.Error as err:
      cnx.reconnect(attempts=12, delay=5)


    # explicitly creating a connection pool
    try:
        mysql_pool = mysql.connector.pooling.MySQLConnectionPool(**mysql_config)
        return mysql_pool
    except mysql.connector.Error as err:
        logger.error(f'prolbem initializing mysql connector pool: {err}')
        raise


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
    formatter = CustomJsonFormatter('%(timestamp)s %(severity)s %(filename)s %(funcName)s %(lineno)s %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)
    return formatter
