from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import List
from typing import Union

from pymongo import DESCENDING

from .infer import T5InferenceService
from dialog_agent_service.app_utils import predict_custom_trained_model_sample
from dialog_agent_service.db import get_mysql_cnx_cursor
from dialog_agent_service.db import mongo_db

MONGO_TIME_STR_FORMAT = '%Y-%m-%dT%H:%M:%S.000Z'
CLEAR_HISTORY_COMMAND = 'CLEAR_HISTORY'

logger = logging.getLogger(__name__)
inference_obj = T5InferenceService('../test_data')

async def get_past_k_turns(user_id: int, service_channel_id: int, vendor_id: str, k: int, window: int):
    """
    ToDo: We need to filter out messages based on time delta. say only < 12 hrs
    Args:
        user_id:
        service_channel_id:
        k: past k turns from now
        window: the window of past n hours
    Returns:
        Tuple of concatenated messages and the vendor name as stored in vendors tabel
    """
    data = await get_user_and_service_number(user_id, service_channel_id, vendor_id)
    # start and end time of the window
    utcnow = datetime.utcnow()
    endtime = utcnow.strftime(MONGO_TIME_STR_FORMAT)
    starttime = (
        utcnow - timedelta(hours=window)
    ).strftime(MONGO_TIME_STR_FORMAT)
    # find past k turns up till now
    docs = mongo_db['messages'].find({
        'serviceNumber': data['serviceNumber'],
        'userNumber': data['userNumber'],
        'createdAt': {'$lt': endtime, '$gt': starttime},
    }).sort('createdAt', DESCENDING).limit(k)
    docs_rev = list(docs)[::-1]
    docs = process_past_k_turns(docs_rev, vendor_id)
    return docs, data['vendorName']


async def get_user_and_service_number(user_id: int, service_channel_id: int, merchant_id: str):
    """
    retrieve the user phone number and service channel phone number from mysql db
    Returns:
        a dict with userNumber, serviceNumber, and vendorName as keys
    Raises:
        exception if no record matches
    """
    query = """
    SELECT
    pn.phoneNumber AS userNumber,
    sc.phoneNumber AS serviceNumber,
    v.name AS vendorName
    FROM phoneNumbersServiceChannels pnsc
    INNER JOIN phoneNumbers pn ON pn.id = pnsc.phoneNumberId
    INNER JOIN serviceChannels sc ON sc.id = pnsc.serviceChannelId
    INNER JOIN serviceChannelsVendors scv ON sc.id = scv.serviceChannelId
    INNER JOIN vendors v ON v.id = scv.vendorId
    WHERE pn.userId = %s AND pn.isPrimary = 1 AND sc.id = %s AND v.id = %s
    """
    with get_mysql_cnx_cursor() as cursor:
        cursor.execute(query, (user_id, service_channel_id, int(merchant_id)))
        data = cursor.fetchone()
    if not data:
        raise Exception(f"""cannot retrieve user and service phone numbers for
            userId {user_id}, serviceChannelId {service_channel_id}, and vendorId {merchant_id}
            """)
    logger.debug(f'retrieved user, service numbers and vendor name: {data}')
    return data


def process_past_k_turns(docs, vendor_id):
    """
    process past k turns
    Returns:
        a list of tuples containing the "direction" and the "body" of the document if the last turn was "inbound"
        else return an empty list
    """
    
    if len(docs) > 0:
        last_message = docs[-1]
        if last_message.get('direction') == 'outbound':
            if last_message.get('senderType') == 'cx':
                # meaning that a CX agent may have already responded
                logger.warning(
                    'There has been a new outbound message since this call was made!',
                )
                return []
            else:  # system message
                # filter the last system message out before sending to model
                # ToDo: more advanced processing to remove the last n (> 1) auto messages
                docs = docs[:-1]
        else:
            #TODO - check if last_message.vendor_id matches current vendor_id, otherwise ignore history           
            #used for testing
            if last_message.get('body') == CLEAR_HISTORY_COMMAND:
                logger.info("COMMAND:CLEAR_HISTORY, ignoring history")
                return []
            
            if len(docs) > 1:
                previous_inbound = docs[-2]
                if previous_inbound.get('body') == CLEAR_HISTORY_COMMAND:
                    #only return last message
                    logger.info("History cleared")
                    docs = docs[-1:]
    
    #TODO - return dict with a subset of keys {k:d[k] for k in l if k in d}
    docs = [(doc.get('direction'), doc.get('body')) for doc in docs]
    return docs


async def run_inference(docs: list[tuple], vendor_name: str, merchant_id: str, project_id: str, endpoint_id: str, task_routing_config: dict = {}):
    """
    call the T5 model service endpoint and generate a response
    ToDo: implement the logic for making multiple calls to the model api here
    """
    def predict_fn(text: str | list[str]):
        if isinstance(text, str):
            text = [text]
        responses = predict_custom_trained_model_sample(
            project=project_id,
            endpoint_id=endpoint_id,
            location=os.getenv('VERTEX_AI_LOCATION', 'us-central1'),
            api_endpoint=os.getenv(
                'VERTEX_AI_ENDPOINT',
                'us-central1-aiplatform.googleapis.com',
            ),
            instances=[{'data': {'context': t}} for t in text]
        )
        return responses
    return inference_obj.infer(docs, vendor_name, merchant_id, predict_fn, task_routing_config=task_routing_config)
