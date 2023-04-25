from __future__ import annotations

import json
import logging
import os
import sys

import flask
import requests
from flask import jsonify
from flask import make_response
from flask import request
from flask_login import login_required
from flask_login import login_user
from flask_login import LoginManager
from oauthlib.oauth2 import WebApplicationClient

from dialog_agent_service import create_app
from dialog_agent_service import init_logger
from dialog_agent_service.app_utils import create_user_contexts, encode_sentence
from dialog_agent_service.app_utils import generate_session_id
from dialog_agent_service.app_utils import generate_uuid
from dialog_agent_service.app_utils import get_google_provider_cfg
from dialog_agent_service.conversational_agent.conversation import handle_conversation_response
from dialog_agent_service.db import get_merchant
from dialog_agent_service.db import get_user_contexts
from dialog_agent_service.db import update_user_contexts
from dialog_agent_service.df_utils import get_df_response
from dialog_agent_service.df_utils import parse_df_response
from dialog_agent_service.search.SemanticSearch import demo_search
from dialog_agent_service.search.SemanticSearch import semanticSearch
from dialog_agent_service.user import User

formatter = init_logger()
logger = logging.getLogger(__name__)

app = create_app()
app.secret_key = os.environ.get('SECRET_KEY')

login_manager = LoginManager()
login_manager.init_app(app)

client = WebApplicationClient(os.environ.get('GOOGLE_CLIENT_ID'))


@app.route('/', methods=['GET'])
def index():
    return 'Dialog Agent Service'


@app.route('/login')
def login():
    # temporary login code
    user = User('1234', 'my_name', 'me@email.com')
    login_user(user)

    if user:
        return flask.redirect(flask.url_for('index'))

    # Google OAuth2 code, should not be hit for now
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg['authorization_endpoint']

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + '/callback',
        scope=['openid', 'email', 'profile'],
    )
    return flask.redirect(request_uri)


@app.route('/login/callback')
def login_callback():
    code = request.args.get('code')

    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg['token_endpoint']

    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code,
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(
            os.environ.get('GOOGLE_CLIENT_ID'),
            os.environ.get('GOOGLE_CLIENT_SECRET'),
        ),
    )

    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg['userinfo_endpoint']
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    if userinfo_response.json().get('email_verified'):
        unique_id = userinfo_response.json()['sub']
        users_email = userinfo_response.json()['email']
        picture = userinfo_response.json()['picture']
        users_name = userinfo_response.json()['given_name']
    else:
        return 'User email not available or not verified by Google.', 400

    user = User(
        id_=unique_id, name=users_name, email=users_email,
    )

    login_user(user)

    return flask.redirect(flask.url_for('index'))


@app.route('/logout')
def logout():
    # logout_user()
    return flask.redirect(flask.url_for('index'))


@login_required
@app.route('/conversation_response', methods=['POST'])
async def conversation_response():
    req = request.get_json(force=True)
    logger.debug(f'request: {req}')
    if req.get('merchantId') is None:
        raise Exception('missing merchant id')
    merchant_id = int(req.get('merchantId'))
    if req.get('userId') is None:
        raise Exception('missing user id')
    user_id = int(req.get('userId'))
    if req.get('serviceChannelId') is None:
        raise Exception('missing service channel id')
    service_channel_id = int(req.get('serviceChannelId'))

    response = await handle_conversation_response(
        merchant_id,
        user_id,
        service_channel_id,
        k=int(req.get('k', 5)),
        window=int(req.get('window', 12)),
        test_merchant=req.get('testMerchant', ''),
    )
    logger.debug(f'response: {response}')
    return make_response(jsonify(response))


@login_required
@app.route('/agent', methods=['POST'])
async def agent():
    """
    receives the POST request from GK, queries DF, and returns the response
    """
    req = request.get_json(force=True)
    validate_req(req)

    # add extra fields to log records to make logs distinct and searchable per user + campaign
    formatter.extras = {
        'user_id': req.get(
            'userId',
        ), 'service_channel_id': req.get('serviceChannelId'),
    }
    logger.info(f'DF webhook request: {req}')
    try:
        resp = await handle_request(req)
    except Exception as e:
        logger.error(f'Something went wrong: {e}')
        raise Exception(e)

    return make_response(jsonify(resp))

@login_required
@app.route('/index_products', methods=['POST'])
def index_products():
    return semanticSearch.index_products()

@login_required
@app.route('/index_faqs')
def index_faqs():
    return semanticSearch.index_faqs()

@login_required
@app.route('/faq')
def faq():
    question = request.args.get('question')
    merchant_id = int(request.args.get('merchantId'))

    site_id = get_merchant(merchant_id)['site_id']

    suggestions = semanticSearch.faq_search(site_id, question)

    return suggestions[0]

@app.route('/get_embedding', methods=['GET'])
def get_embedding():
    query = request.args.get('query')

    endpoint_id = os.getenv('ST_VERTEX_AI_ENDPOINT_ID')
    project_id = os.getenv('VERTEX_AI_PROJECT_ID')

    return encode_sentence(query, project_id, endpoint_id)


@app.route('/index_demo')
def index_demo():
    return demo_search.index_demo()


@app.route('/faq_demo')
def faq_demo():
    question = request.args.get('question')

    return demo_search.faq_demo(question)


def validate_req(req: dict) -> None:
    if req.get('userId') is None \
            or req.get('serviceChannelId') is None \
            or req.get('payload') is None \
            or req.get('flowType') is None \
            or not req.get('text'):
        raise Exception(f'a required param is missing from the request: {req}')


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

    df_resp: dict | None = await get_df_response(req, user_contexts)
    resp = parse_df_response(df_resp, req.get('vendorId'))
    if df_resp and df_resp['query_result']['output_contexts']:
        await update_user_contexts(doc_id, df_resp['query_result']['output_contexts'])
    return resp

if __name__ == '__main__':
    port = os.getenv('DIALOG_AGENT_SERVICE_PORT', 8080)
    app.run(host='0.0.0.0', port=port)
