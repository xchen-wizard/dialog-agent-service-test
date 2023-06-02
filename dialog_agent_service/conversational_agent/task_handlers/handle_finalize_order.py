import ast
import logging
from dialog_agent_service.actions.order_summary_actions import create_order_summary_message
logger = logging.getLogger(__name__)


def handle_finalize_order(cnv_obj=None, merchant_id=None, current_cart=None, predict_fn=None, **kwargs):
    message = create_order_summary_message(current_cart['id'])
    logger.debug('order summary message:', message)
    return {
        'response': message,
        'vendorId': int(merchant_id),
    }
