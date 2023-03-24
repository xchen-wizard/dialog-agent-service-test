from __future__ import annotations

import logging
import os
from collections import defaultdict
from collections import namedtuple
from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import List
from typing import Union

from bson.objectid import ObjectId
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value
from pymongo import ASCENDING

from .infer import T5InferenceService
from .response import *
from dialog_agent_service.db import get_mysql_cnx_cursor
from dialog_agent_service.db import mongo_db

logger = logging.getLogger(__name__)
MONGO_TIME_STR_FORMAT = '%Y-%m-%dT%H:%M:%S.000Z'
SPEAKER_TAGS = {'inbound': 'Buyer:', 'outbound': 'Seller:'}
inference_obj = T5InferenceService('../test_data')
ProductResponseUnion = namedtuple(
    'ProductResponseUnion', ['products', 'response'],
)
FUZZY_MATCH_THRESHOLD = 90


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
    # start and end time of the window
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
    docs = process_past_k_turns(list(docs))
    return docs, data['vendorName']


async def get_user_and_service_number(user_id: int, service_channel_id: int, vendor_id: int):
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
        cursor.execute(query, (user_id, service_channel_id, vendor_id))
        data = cursor.fetchone()
    if not data:
        raise Exception(f"""cannot retrieve user and service phone numbers for
            userId {user_id}, serviceChannelId {service_channel_id}, and vendorId {vendor_id}
            """)
    logger.debug(f'retrieved user, service numbers and vendor name: {data}')
    return data


def process_past_k_turns(docs):
    """
    process past k turns
    Returns:
        a list of tuples containing the "direction" and the "body" of the document if the last turn was "inbound"
        else return an empty list
    """
    if len(docs) > 0 and docs[-1].get('direction') == 'outbound':
        if docs[-1].get('senderType') == 'cx':
            # meaning that a CX agent may have already responded
            logger.warning(
                'There has been a new outbound message since this call was made!',
            )
            return []
        else:  # system message
            # filter the last system message out before sending to model
            # ToDo: more advanced processing to remove the last n (> 1) auto messages
            docs = docs[:-1]
    docs = [(doc.get('direction'), doc.get('body')) for doc in docs]
    return docs


async def run_inference(docs: list[tuple], vendor_name: str, merchant_id: str, project_id: str, endpoint_id: str):
    """
    call the T5 model service endpoint and generate a response
    ToDo: implement the logic for making multiple calls to the model api here
    """
    conversation = [
        ' '.join([SPEAKER_TAGS[direction], message])
        for direction, message in docs
    ]
    conversation = '\n'.join(conversation)  # type: ignore
    logger.debug(f'conversation context: {conversation}')

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
            instances=[{'data': {'context': t}} for t in text],
        )
        return responses
    ret = inference_obj.infer(conversation, vendor_name, predict_fn)
    # product search lookup if cart is present
    if 'cart' in ret and len(ret['cart']) > 0:
        resolved_cart = []
        for product, qty in ret['cart']:
            products, response = match_product_variant(merchant_id, product)
            if products:
                resolved_cart.extend([(p[0], p[1], qty) for p in products])
            if response:
                ret['response'] = response + '\n' + ret.get('response', '')
        ret['response'] = gen_cart_response(
            resolved_cart,
        ) + '\n' + ret.get('response', '')
        ret['cart'] = [(name, qty) for (name, _, qty) in resolved_cart]
        return ret
    return ret


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


def get_merchant(merchant_id: int):
    query = """
  SELECT
    id,
    name,
    siteId
  FROM vendors
  WHERE id = %s
  """

    with get_mysql_cnx_cursor() as cursor:
        cursor.execute(query, [merchant_id])
        data = cursor.fetchone()

    return {'id': data.get('id'), 'name': data.get('name'), 'site_id': data.get('siteId')}



def get_merchant_site_ids():
    query = """
  SELECT
    id,
    siteId
  FROM vendors
  """

    with get_mysql_cnx_cursor() as cursor:
        cursor.execute(query)
        data = cursor.fetchall()

    merchants = {}

    for merchant in data:
        merchants[str(merchant['id'])] = merchant['siteId']

    return merchants


def get_variants(variant_ids: list):

    object_ids = list(map(ObjectId, variant_ids))

    variant_cursor = mongo_db['productVariants'].find(
        {'_id': {'$in': object_ids}},
    )

    variants = []

    for variant in variant_cursor:
        product = mongo_db['productCatalog'].find_one(
            {'_id': ObjectId(variant['productId'])},
        )
        variant['product'] = product

        listings = list(
            mongo_db['productListings'].find(
                {'productVariantId': str(variant['_id'])},
            ),
        )
        variant['listings'] = listings

        variants.append(variant)

    return variants


def get_all_variants_by_merchant_id():
    """
    queries the mongo products collections and compile a dict of {merchantId: {productName: {variantName: price}}}
    """
    ret_dict = defaultdict(lambda: defaultdict(dict))
    variant_cursor = mongo_db['productVariants'].find()

    variants = []

    for variant in variant_cursor:
        try:
            product_id = ObjectId(variant['productId'])
            product = mongo_db['productCatalog'].find_one({'_id': product_id})
            variant['product'] = product

            listings = list(
                mongo_db['productListings'].find(
                    {'productVariantId': str(variant['_id'])},
                ),
            )
            variant['listings'] = listings

            # name = variant['product']['name'] + ' - ' + variant['name']

            # price =  variant['listings'][0]['price']
            ret_dict[variant['merchantId']][variant['product']['name']][variant['name']] = variant['listings'][0][
                'price'
            ]
        except Exception as e:
            logger.error(f'no product id found in doc: {variant}')
    return ret_dict


def get_all_variants():
    variant_names = {}

    products = mongo_db['productCatalog'].find()

    for product in products:
        variants = mongo_db['productVariants'].find(
            {'productId': str(product['_id'])},
        )

        for variant in variants:
            name = product['name'] + ' - ' + variant['name']
            variant_names[variant['_id']] = {
                'name': name, 'merchant_id': product['merchantId'],
            }

    return variant_names


def match_product_variant(merchant_id: int, product_name: str) -> ProductResponseUnion:
    merchant_id = str(merchant_id)
    product_matches = process.extract(
        product_name, VARIANTS_OBJ[merchant_id].keys(), scorer=fuzz.token_set_ratio,
    )
    significant_matches = [
        tup[0]
        for tup in product_matches if tup[1] > FUZZY_MATCH_THRESHOLD
    ]
    if len(significant_matches) > 2:
        logger.debug(
            f'{product_name} matched to many product names: {significant_matches}. No match returned',
        )
        return ProductResponseUnion(
            None, gen_non_specific_product_response(
                product_name, significant_matches[0], significant_matches[1], significant_matches[2],
            ),
        )
    else:
        products = []
        response = ''
        for product_match in significant_matches:
            variant_matches = [
                (
                    product_name + ' - ' +
                    tup[0], VARIANTS_OBJ[merchant_id][product_match][tup[0]],
                )
                for tup in process.extract(product_match, VARIANTS_OBJ[merchant_id][product_match].keys(), scorer=fuzz.token_set_ratio)
                if tup[1] > FUZZY_MATCH_THRESHOLD
            ]
            if len(variant_matches) > 0:
                products.extend(variant_matches)
            else:
                response += '\n' + gen_variant_selection_response(
                    product_match, VARIANTS_OBJ[merchant_id][product_match].keys(
                    ),
                )

        return ProductResponseUnion(products, response)


# this is loaded during the start-up and will have to be restarted after a mongo product update
# ToDo: not ideal, replace later
VARIANTS_OBJ = get_all_variants_by_merchant_id(
) if os.getenv('UNITTEST') != 'true' else {}
logger.info('loaded product variants!')

def get_all_faqs():
  faq_query = """
  SELECT 
    v.siteId AS siteId,
    q.text AS question,
    a.text AS answer
  FROM
    faqs q
  JOIN
    faqs a
  ON 
    q.answerId = a.id
  JOIN
    vendors v
  ON
    q.merchantId = v.id
  WHERE
    q.type = 'question' OR q.type = 'questionExpansion' OR q.type = 'questionExtraction'
  """

  with get_mysql_cnx_cursor() as cursor:
      cursor.execute(faq_query)
      data = cursor.fetchall()

  faqs = {}

  for faq in data:
     if faq['siteId'] not in faqs:
        faqs[faq['siteId']] = {}
        
     faqs[faq['siteId']][faq['question']] = faq['answer']

  return faqs


def encode_sentence(query: str, project_id: str, endpoint_id: str):
  embeddings = predict_custom_trained_model_sample(
      project=project_id,
      endpoint_id=endpoint_id,
      location=os.getenv('VERTEX_AI_LOCATION', 'us-central1'),
      instances={"instances": [{"data": {"query": query}}]} 
  )

  return embeddings['predictions'][0]
