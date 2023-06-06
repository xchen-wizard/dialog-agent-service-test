import ast
import logging
from dialog_agent_service.actions.order_summary_actions import create_order_summary_message
from .handle_create_or_update_order_cart import handle_create_or_update_order_cart
from dialog_agent_service.utils.utils import handler_to_task_name
logger = logging.getLogger(__name__)


def handle_finalize_order(cnv_obj=None, merchant_id=None, current_cart=None, predict_fn=None, **kwargs):
    task = handler_to_task_name()
    if not current_cart.get('lineItems', None):
        # Cart cannot be empty. This implies a model misprediction
        return handle_create_or_update_order_cart(cnv_obj, merchant_id, current_cart, predict_fn)
    response = create_order_summary_message(current_cart['id'])
    message = ''.join([part['body'] for part in response['content']])
    logger.debug('order summary message:', message)
    return {
        'task': task,
        'response': message,
        'vendorId': int(merchant_id),
    }
