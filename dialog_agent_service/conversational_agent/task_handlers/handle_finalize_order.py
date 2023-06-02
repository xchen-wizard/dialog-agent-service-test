import ast

import logging
logger = logging.getLogger(__name__)

def handle_finalize_order(cnv_obj=None, merchant_id=None, current_cart=None, predict_fn=None, **kwargs):
    return {
        'messageType': 'order-summary',
        'cartId': current_cart['id'],
        'cartStateId': current_cart['cartState']['id'],
        'vendorId': int(merchant_id),
    }