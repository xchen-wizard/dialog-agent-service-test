from __future__ import annotations

import logging

from dialog_agent_service.conversational_agent.conversation_utils import process_past_k_turns
from dialog_agent_service.constants import HISTORY_CLEARED

logger = logging.getLogger()


def test_process_past_k_turns_clear_history():
    docs = [
        {'direction': 'outbound', 'body': 'test'},
        {'direction': 'inbound', 'body': 'clear_history '},
    ]
    actual = process_past_k_turns(docs)
    expected = ([], True)
    assert actual == expected


def test_process_past_k_turns_truncate_history():
    docs = [
        {'direction': 'outbound', 'body': 'test'},
        {'direction': 'inbound', 'body': 'clear_history '},
        {'direction': 'outbound', 'body': HISTORY_CLEARED},
        {'direction': 'outbound', 'body': 'test'},
        {'direction': 'inbound', 'body': 'CLEAR_HISTORY'},
        {'direction': 'outbound', 'body': HISTORY_CLEARED},
        {'direction': 'inbound', 'body': 'test'},
        {'direction': 'outbound', 'body': 'test'},
        {'direction': 'inbound', 'body': 'test'},
    ]
    actual = process_past_k_turns(docs)
    expected = ([('inbound', 'test'), ('outbound', 'test'),
                ('inbound', 'test')], False)
    logger.info(actual)
    assert actual == expected


def test_process_past_k_turns_truncate_history_without_server_response():
    docs = [
        {'direction': 'outbound', 'body': 'test'},
        {'direction': 'inbound', 'body': 'clear_history '},
        {'direction': 'outbound', 'body': HISTORY_CLEARED},
        {'direction': 'outbound', 'body': 'test'},
        {'direction': 'inbound', 'body': 'CLEAR_HISTORY'},
        {'direction': 'inbound', 'body': 'test'},
        {'direction': 'outbound', 'body': 'test'},
        {'direction': 'inbound', 'body': 'test'},
    ]
    actual = process_past_k_turns(docs)
    expected = ([('inbound', 'test'), ('outbound', 'test'),
                ('inbound', 'test')], False)
    logger.info(actual)
    assert actual == expected