from __future__ import annotations

import logging

from dialog_agent_service.conversational_agent.infer import match_product_variant


logger = logging.getLogger()


def test_match_product_variant():
    # ToDO: if we are doing 2-step matching, we'll need to lower the FUZZY_MATCH_THRESHOLD for the second step to work
    # currently this test is merely to see that the code runs.
    returned = match_product_variant('53', 'sweet baby orange shampoo 8oz')
    logger.info(returned)
