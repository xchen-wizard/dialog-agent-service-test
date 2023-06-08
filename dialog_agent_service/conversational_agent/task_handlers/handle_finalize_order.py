import ast
import logging
from dialog_agent_service.actions.cart_actions import cart_go_to_review_order
from dialog_agent_service.actions.order_summary_actions import create_order_summary_message
from .handle_create_or_update_order_cart import handle_create_or_update_order_cart
from dialog_agent_service.utils.utils import handler_to_task_name
logger = logging.getLogger(__name__)


def handle_finalize_order(cnv_obj=None, merchant_id=None, current_cart=None, predict_fn=None, **kwargs):
    task = handler_to_task_name()
    if not current_cart.get('lineItems', None):
        # Cart cannot be empty. This implies a model misprediction
        return handle_create_or_update_order_cart(cnv_obj, merchant_id, current_cart, predict_fn, task=task)
    cart_id = current_cart['id']

    if 'cartState' in current_cart and 'id' in current_cart['cartState'] and current_cart['cartState']['id'] == 4:
        cart_go_to_review_order(cart_id)
    response = create_order_summary_message(cart_id)

    message = ''.join([part['body'] for part in response['content']])
    logger.debug('order summary message:', message)
    return {
        'task': task,
        'message-type': 'order-summary',
        'cartId': current_cart['id'],
        'cartStateId': current_cart['cartState']['id'],
        'response': message,
        'vendorId': int(merchant_id),
    }
