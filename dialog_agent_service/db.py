from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from contextlib import contextmanager
from typing import Any

import mysql

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
