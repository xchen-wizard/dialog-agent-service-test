from __future__ import annotations

import logging
import os
from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import List
from typing import Union

from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value
from pymongo import ASCENDING

from .infer import T5InferenceService
from dialog_agent_service.db import get_mysql_cnx_cursor
from dialog_agent_service.db import mongo_db

logger = logging.getLogger(__name__)
MONGO_TIME_STR_FORMAT = '%Y-%m-%dT%H:%M:%S.000Z'
SPEAKER_TAGS = {'inbound': 'Buyer:', 'outbound': 'Seller:'}

inference_obj = T5InferenceService('../test_data')


async def get_past_k_turns(user_id: int, service_channel_id: int, vendor_id: int, k: int, window: int):
    """
    ToDo: We need to filter out messages based on timedelta. say only < 12 hrs
    Args:
        user_id:
        service_channel_id:
        k: past k turns from now
        window: the window of past n hours
    Returns:
        Tuple of concatenated messages and the vendor name as stored in vendors tabel
    """
    data = await get_user_and_service_number(user_id, service_channel_id, vendor_id)
    utcnow = datetime.utcnow()
    endtime = utcnow.strftime(MONGO_TIME_STR_FORMAT)
    starttime = (
        utcnow - timedelta(hours=window)
    ).strftime(MONGO_TIME_STR_FORMAT)
    # find past k turns up till now
    docs = mongo_db['messages'].find({
        'userNumber': data['userNumber'],
        'serviceNumber': data['serviceNumber'],
        'createdAt': {'$lt': endtime, '$gt': starttime},
    }).sort('createdAt', ASCENDING).limit(k)
    docs = process_past_k_turns(docs)
    return docs, data['vendorName']


async def get_user_and_service_number(user_id: int, service_channel_id: int, vendor_id: int):
    """
    retrieve the user phone number and service channel phone number from mysql db
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
        cursor.execute(query, (user_id, service_channel_id, vendor_id))
        data = cursor.fetchone()
    logger.debug(f'retrieved user, service numbers and vendor name: {data}')
    return data


def process_past_k_turns(docs):
    """
    process past k turns
    ToDo: how to account for auto-generated outbound messages like OOTO reply etc.
    Returns:
        a list of tuples containing the "direction" and the "body" of the document if the last turn was "inbound"
        else return an empty list
    """
    if len(docs) > 0 and docs[-1].get('direction') == 'outbound':
        if docs[-1].get('senderType') == 'cx':
            # meaning that a CX agent may have already responded or a new outbound message has been auto-sent
            logger.warning(
                'There has been a new outbound message since this call was made!',
            )
            return []
        else:  # system message
            # filter the last system message out before sending to model
            docs = docs[:-1]
    docs = [(doc.get('direction'), doc.get('body')) for doc in docs]
    return docs


async def run_inference(docs: list[tuple], vendor_name: str, project_id: str, endpoint_id: str):
    """
    call the T5 model service endpoint and generate a response
    ToDo: implement the logic for making multiple calls to the model api here
    """
    conversation = [
        ' '.join([SPEAKER_TAGS[direction], message])
        for direction, message in docs
    ]
    conversation = '\n'.join(conversation)  # type: ignore

    def predict_fn(text: str | list[str]):
        if isinstance(text, str):
            text = [text]
        responses = predict_custom_trained_model_sample(
            project=project_id,
            endpoint_id=endpoint_id,
            location='us-central1',
            instances=[{'data': {'context': t}} for t in text],
        )
        return responses
    return inference_obj.infer(conversation, vendor_name, predict_fn)


def predict_custom_trained_model_sample(
    project: str,
    endpoint_id: str,
    instances,
    location: str = 'us-central1',
    api_endpoint: str = 'us-central1-aiplatform.googleapis.com',
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
    # The predictions are a google.protobuf.Value representation of the model's predictions.
    predictions = response.predictions
    return predictions
