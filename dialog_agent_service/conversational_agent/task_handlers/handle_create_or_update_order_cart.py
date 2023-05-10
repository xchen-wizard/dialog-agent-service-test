from ..chatgpt import generate_cart_mentions
from ..resolve_cart import resolve_cart


def handle_create_or_update_order_cart(cnv_obj=None, merchant_id=None, current_cart=None):
    model_predicted_cart = generate_cart_mentions(cnv_obj, current_cart)
    cart, response = resolve_cart(merchant_id, model_predicted_cart)
    return {
        'cart': cart,
        'response': response,
        'model_predicted_cart': model_predicted_cart
    }
