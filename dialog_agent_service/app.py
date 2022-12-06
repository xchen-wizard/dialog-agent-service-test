from __future__ import annotations

import logging
import os
import sys

import flask
from flask import jsonify
from flask import make_response
from flask import request

from dialog_agent_service import create_app, init_logger
from dialog_agent_service.app_utils import generate_session_id, generate_uuid, create_user_contexts
from dialog_agent_service.db import get_user_contexts
from dialog_agent_service.df_utils import get_df_response, parse_df_response


formatter = init_logger()
logger = logging.getLogger(__name__)

app = create_app()


@app.route('/')
def index():
    return 'Dialog Agent Service'


@app.route('/agent', methods=['POST'])
async def agent():
    """
    receives the POST request from GK, queries DF, and returns the response
    """
    req = request.get_json(force=True)
    validate_req(req)

    # add extra fields to log records to make logs distinct and searchable per user + campaign
    formatter.extras = {'user_id': req.get('userId'), 'service_channel_id': req.get('serviceChannelId')}
    logger.info(f'DF webhook request: {req}')
    try:
        resp = await handle_request(req)
    except Exception as e:
        logger.error(f'Something went wrong: {e}')
        raise Exception(e)

    return make_response(jsonify(resp))


def validate_req(req: dict) -> None:
    if req.get('userId') is None \
            or req.get('serviceChannelId') is None \
            or req.get('payload') is None \
            or req.get('flowType') is None \
            or not req.get('text'):
        raise Exception(f"a required param is missing from the request: {req}")


async def handle_request(req: dict) -> dict:
    """
    Process the incoming request and get a response from Dialogflow
    1. construct context if not already existing in MongoDB
    2. sends query to DF awaiting response
    3. parse response from DF and transform to GK compatible format
    4. stores DF contexts in MongoDB

    """
    session_id = generate_session_id(req)
    doc_id = generate_uuid(session_id)
    user_contexts = await get_user_contexts(doc_id)
    if user_contexts is None:
        # create new contexts
        user_contexts = await create_user_contexts(req, session_id, doc_id)
    logger.debug(f'DF user contexts: {user_contexts}')

    df_resp = await get_df_response(req, user_contexts)
    resp = parse_df_response(df_resp)
    return resp


if __name__ == '__main__':
    if not os.getenv('AGENT_TYPE'):
        raise Exception("Missing env var AGENT_TYPE")
    if os.getenv('AGENT_TYPE').lower() != 'dialogflow':
        raise Exception("We currently only support DialogFlow!")
    if not os.getenv('DIALOGFLOW_PROJECT_ID'):
        raise Exception("Missing dialogflow project id!")
    if not os.getenv('DIALOGFLOW_ENVIRONMENT'):
        raise Exception("Missing dialogflow environment")
    port = os.getenv('DIALOG_AGENT_SERVICE_PORT', 8080)
    app.run(host='0.0.0.0', port=port)
