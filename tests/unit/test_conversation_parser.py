from __future__ import annotations

import logging

from dialog_agent_service.conversational_agent.conversation_parser import Conversation

logger = logging.getLogger(__name__)


def test_conversation():
    docs = [
        ('inbound', 'hello'),
        ('outbound', 'hi there'),
        ('outbound', 'what can i do for you?'),
        ('inbound', 'nothing really'),
        ('inbound', 'bye'),
        ('inbound', 'see you next time!'),
    ]
    conv = Conversation(docs)
    for turn in conv.turns:
        logger.info(turn)
    assert conv.n_turns == 3
