from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from collections import defaultdict
from contextlib import contextmanager
from typing import Any

import mysql
from bson.objectid import ObjectId

from dialog_agent_service import init_mongo_db
from dialog_agent_service import init_mysql_db

logger = logging.getLogger(__name__)

mysql_pool = init_mysql_db()  # type: ignore
mongo_db = init_mongo_db()  # type: ignore

@contextmanager
def get_mysql_cnx_cursor():
    try:
        cnx = mysql_pool.get_connection()

        cursor = cnx.cursor(dictionary=True, buffered=True)
        yield cursor
    except mysql.connector.Error as err:
        logger.error(
            f'problem getting connection from pool or creating a cursor object {err}',
        )
    finally:
        cursor.close()
        logger.debug('closing cursor')
        cnx.close()
        logger.debug('returning connection to pool')


async def get_user_contexts(doc_id: str) -> dict | None:
    """
    Get the user contexts stored in mongodb.spt.DialogflowContexts collection.
    Returns:

    """
    data = mongo_db['DialogflowContexts'].find_one({'_id': doc_id})
    logger.debug(
        f'retrieved data from mongo DialogflowContexts collection:\n{data}',
    )
    return data


async def update_user_contexts(doc_id: str, user_contexts: list[dict]) -> dict | None:
    """"
    Find and update the contexts in Mongo DialogflowContexts collection
    Args:
        doc_id: the document id
        user_contexts: the new contexts
    Returns:
        the original doc, which would've been replaced by the new doc
    """
    data = mongo_db['DialogflowContexts'].find_one_and_update(
        {'_id': doc_id},
        {'$set': {'contexts': user_contexts}},
        upsert=True,
    )
    logger.debug(
        f"updating doc {data.get('_id')} in mongo DialogflowContexts collection",
    )
    return data


async def get_campaign_products(campaign_id: int) -> list[dict] | None:
    """
    Retrieves campaign products from mysql campaignProducts table
    Args:
        campaign_id: the unique campaign id
    Returns:
        a list of products associated with the campaign
    """
    query = """
    SELECT productId, retailerId, defaultQuantity, maxQuantity
    FROM campaignProducts
    WHERE campaignId = %s
    """
    with get_mysql_cnx_cursor() as cursor:
        cursor.execute(query, (campaign_id,))
        data = cursor.fetchall()
    logger.debug(f'Get campaign products for campaign {campaign_id}: {data}')
    return data


async def get_campaign_variant_type(campaign_id: int) -> int | None:
    """
    get campaignFlowType for campaignId
    Returns:
        the campaign flow type as an int or None
    """
    query = """
    SELECT campaignFlowType FROM campaigns
    WHERE id = %s
    """

    with get_mysql_cnx_cursor() as cursor:
        cursor.execute(query, (campaign_id,))
        data = cursor.fetchone()
    logger.debug(f'fetched products for campaign {campaign_id}')
    return data.get('campaignFlowType')


def get_merchant(merchant_id: str):
    query = """
      SELECT
        v.id,
        v.name,
        v.siteId,
        r.id as retailerId
      FROM 
        vendors v
      JOIN
        retailers r
      ON
        v.name = r.name
      WHERE v.id = %s
    """
  

    with get_mysql_cnx_cursor() as cursor:
        cursor.execute(query, [int(merchant_id)])
        data = cursor.fetchone()

    return {'id': data.get('v.id'), 'name': data.get('v.name'), 'site_id': data.get('v.siteId'), 'retailerId': data.get('r.id')}


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
                    {
                        'productVariantId': str(
                            variant['_id'],
                        ), 'status': 'active',
                    },
                ),
            )
            variant['listings'] = listings

            # name = variant['product']['name'] + ' - ' + variant['name']

            # price =  variant['listings'][0]['price']
            if len(listings) > 0:
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
            listings = list(
                mongo_db['productListings'].find(
                    {
                        'productVariantId': str(
                            variant['_id'],
                        ), 'status': 'active',
                    },
                ),
            )

            if len(listings) == 0:
                continue

            name = product['name'] + ' - ' + variant['name']
            variant_names[variant['_id']] = {
                'name': name, 'merchant_id': product['merchantId'],
            }

    return variant_names


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
