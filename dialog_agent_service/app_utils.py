from __future__ import annotations

import asyncio
import logging
import os
import uuid
import requests

from dialog_agent_service.data_types import FlowType
from dialog_agent_service.db import get_campaign_products
from dialog_agent_service.db import get_campaign_variant_type

logger = logging.getLogger(__name__)

NAMESPACE = uuid.UUID(os.getenv('MONGO_UUID_NAMESPACE'))
DIALOGFLOW_SESSION_ID_CHAR_LIMIT = 36
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

def get_google_provider_cfg():
    try:
      return requests.get(GOOGLE_DISCOVERY_URL).json()
    except:
        logger.error('error connecting to Google provider')


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
