from __future__ import annotations

import asyncio
import logging
import os
import uuid

import requests
from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.json_format import MessageToDict
from google.protobuf.struct_pb2 import Value

from dialog_agent_service.data_types import FlowType
from dialog_agent_service.db import get_campaign_products
from dialog_agent_service.db import get_campaign_variant_type

logger = logging.getLogger(__name__)

NAMESPACE = uuid.UUID(os.getenv('MONGO_UUID_NAMESPACE'))
DIALOGFLOW_SESSION_ID_CHAR_LIMIT = 36
GOOGLE_DISCOVERY_URL = (
    'https://accounts.google.com/.well-known/openid-configuration'
)


def get_google_provider_cfg():
    try:
        return requests.get(GOOGLE_DISCOVERY_URL).json()
    except Exception as e:
        logger.error(f'error connecting to Google provider: {e}')


def generate_session_id(req: dict) -> str:
    """
    Generate a unique session id based on input depending on flow type
    Returns:
        a string in the format of {flowType}-{userId}-{serviceChannelId}Optional[-{accessoryId}]
        The accessoryId is flow-dependent and can be left out for some flows like "welcome"
    """
    # flowType str format is a little murky, but it should at least be
    # campaign, checkout, welcome, or campaign-variant_1, checkout-variant_1
    # for the variant of each flowType, we can either get it from GK or from the db
    flow_type = req['flowType'].split('-', 1)[0]
    if flow_type == FlowType.CAMPAIGN.value:
        session_id = f"{flow_type}-{req['userId']}-{req['serviceChannelId']}-{req['payload']['campaignId']}"
    elif flow_type == FlowType.CHECKOUT.value:
        session_id = f"{flow_type}-{req['userId']}-{req['serviceChannelId']}-{req['payload']['cartId']}"
    elif flow_type == FlowType.WELCOME.value:
        session_id = f"{flow_type}-{req['userId']}-{req['serviceChannelId']}"
    else:
        raise NotImplementedError(f'{flow_type} is not supported!')
    if len(session_id) > DIALOGFLOW_SESSION_ID_CHAR_LIMIT:
        raise Exception(
            f'Session ID must not exceed {DIALOGFLOW_SESSION_ID_CHAR_LIMIT}:\n{session_id}',
        )
    logger.debug(f'session_id: {session_id}')
    return session_id


def generate_uuid(session_id):
    return str(uuid.uuid5(NAMESPACE, session_id))


async def create_user_contexts(req: dict, session_id: str, doc_id: str, variant_type: str = None) -> dict:
    if req['flowType'].startswith(FlowType.CAMPAIGN.value):
        # create session str
        if variant_type:
            # retrieve campaign products and create initial contexts
            products = await get_campaign_products(req['payload']['campaignId'])
        else:
            variant_type, products = await asyncio.gather(
                get_campaign_variant_type(
                    req['payload']['campaignId'],
                ),  # type: ignore
                get_campaign_products(
                    req['payload']['campaignId'],
                ),  # type: ignore
            )
        if not products:
            raise Exception(
                f"no products defined for campaign {req['payload']['campaignId']}",
            )
        if not variant_type:
            raise Exception(
                f"no variant type defined for campaign {req['payload']['campaignId']}",
            )
        session_str = 'projects/{}/agent/environments/{}/users/{}/sessions/{}'.format(
            os.environ['DIALOGFLOW_PROJECT_ID'],
            os.environ['DIALOGFLOW_ENVIRONMENT'],
            req.get('userId'),
            session_id,
        )
        contexts = [
            {
                'name': '{}/contexts/{}'.format(session_str, str(variant_type) + '-followup'),
                'lifespan_count': 2,
            },
            {
                'name': f'{session_str}/contexts/session-vars',
                'lifespan_count': 50,
                'parameters': {'products': [{'isSelected': False, **d} for d in products]},
            },
        ]
        return {
            '_id': doc_id,
            'sessionStr': session_str,
            'contexts': contexts,
        }
    else:
        raise NotImplementedError(f"{req['flowType']} is not yet supported!")


def predict_custom_trained_model_sample(
    project: str,
    endpoint_id: str,
    instances,
    location: str = 'us-central1',
    api_endpoint: str = 'us-central1-aiplatform.googleapis.com'
):
    """
    `instances` can be either single instance of type dict or a list
    of instances.
    Returns:
        list of strings containing the generated texts
    """
    # The AI Platform services require regional API endpoints.
    client_options = {'api_endpoint': api_endpoint}
    # Initialize client that will be used to create and send requests.
    # This client only needs to be created once, and can be reused for multiple requests.
    client = aiplatform.gapic.PredictionServiceClient(
        client_options=client_options,
    )
    # The format of each instance should conform to the deployed model's prediction input schema.
    instances = instances if type(instances) == list else [
        instances,
    ]
    instances = [
        json_format.ParseDict(
            instance_dict, Value(),
        ) for instance_dict in instances
    ]
    parameters_dict = {}  # type: ignore
    parameters = json_format.ParseDict(parameters_dict, Value())
    endpoint = client.endpoint_path(
        project=project, location=location, endpoint=endpoint_id,
    )
    response = client.predict(
        endpoint=endpoint, instances=instances, parameters=parameters,
    )
    # convert protobuf to regular python object
    response = MessageToDict(response._pb)
    # The predictions are a google.protobuf.Value representation of the model's predictions.
    predictions = response.get('predictions')
    return predictions


def encode_sentence(query: str, project_id: str, endpoint_id: str):
    embeddings = predict_custom_trained_model_sample(
        project=project_id,
        endpoint_id=endpoint_id,
        location=os.getenv('VERTEX_AI_LOCATION', 'us-central1'),
        instances=[{'data': {'query': query}}],
    )

    return embeddings[0]
