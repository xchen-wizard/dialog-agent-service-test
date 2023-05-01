from __future__ import annotations

import logging
import time

import pytest

from dialog_agent_service import get_gql_access_token
from dialog_agent_service import init_gql
from dialog_agent_service.db import product_search

logger = logging.getLogger()


def test_get_gql_access_token():
    resp = get_gql_access_token()
    assert resp is not None
    logger.debug(resp.get('merchantUserLogin').get('accessToken'))
    assert resp.get('merchantUserLogin').get('accessToken') is not None


def test_init_gql():
    client = init_gql()
    assert client is not None


def test_product_search():
    start = time.time()
    resp = product_search('6', 'large')
    end = time.time()
    logger.info(resp)
    logger.info(end - start)
