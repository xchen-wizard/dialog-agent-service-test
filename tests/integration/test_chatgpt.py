import logging

from dialog_agent_service.conversational_agent.chatgpt import llm_retrieval
from dialog_agent_service.das_exceptions import LLMOutputValidationFailed
import pytest

logger = logging.getLogger()


def test_llm_retrieval():
    queries = [
        "Can I only exchange my apparel if they're in perfect condition?",
        "Do you offer exchange for apparel?"
    ]
    docs = """
        returnRefundPolicy
If your item is missing, please contact the shipping provider and file a claim. Once your claim is filed, please provide us with your claim number and we will re-ship your order. We don’t offer refunds on our products because they are consumable goods and it would present a safety risk for us to resell or re-use.
For apparel and accessories, we offer exchange only within 30 days.
No refunds/exchanges on discounted or limited-edition items.

FAQ
QUESTION: WHAT IS YOUR RETURN POLICY?
ANSWER: We don’t offer refunds on our products because they are consumable goods and it would present a safety risk for us to resell or re-use. 
For apparel and accessories, we offer exchange only within 30 days.
No refunds/exchanges on discounted or limited-edition items.

FAQ
QUESTION: CAN I SWITCH MY SUBSCRIPTION FLAVORS?
ANSWER: Absolutely! We'd be happy to help. What would you like to change your [flavor] subscription to?

FAQ
QUESTION: HOW LONG DOES IT TAKE TO RECEIVE MY G.O.A.T. FUEL® ORDER ONCE I PLACE MY ORDER?
ANSWER: Shipping is always FREE and orders take approximately 3-5 business days to arrive.

FAQ
QUESTION: Can I invest in GOAT Fuel stock?
ANSWER: Currently, we are a privately owned company and does not offer stock for public investment. However, we truly appreciate your desire to invest in us!

FAQ
QUESTION: Do you ship to Canada?
ANSWER: Unfortunately we currently only ship within the United States. Things are always changing, though, and in the case that we expand to Canada in the future, we'll be sure to let you know! 

FAQ
QUESTION: Where can I find GOAT Fuel in stores near me?
ANSWER: We are currently available in stores at select big box retailers such as Safeway, Luckys, Target, Publix and HEB’s Central Market. Use our store locator to check availability near you! https://goatfuel.com/pages/find-a-store 

FAQ
QUESTION: Is there a maximum number of orders I can place over text?
ANSWER: There is no maximum number of orders you can place over text.

FAQ
QUESTION: Can I use Shop Pay to purchase GOAT Fuel products?
ANSWER: Yes, you can use Shop Pay as an option with express checkout on the GOAT Fuel website at goatfuel.com.
        """
    with pytest.raises(LLMOutputValidationFailed) as e:
        llm_retrieval(queries[0], docs)

    logger.info(e)

    response = llm_retrieval(queries[1], docs)
    logger.info(response)