import ast
from ..chatgpt import generate_cart_mentions
from ..resolve_cart import gen_disambiguation_response, match_mentions_to_products, get_product_price
from .handle_recommend_product import handle_recommend_product
from ..response import gen_cart_response, gen_opening_response
import logging
logger = logging.getLogger(__name__)


def create_input_cart_mentions(cnv_obj, current_cart):
    context = "\n".join([str(t) for t in cnv_obj.turns[:-2]]) if cnv_obj.n_turns > 2 else ""
    last_seller_utt = str(cnv_obj.turns[-2]) if cnv_obj.n_turns > 1 else ""
    prompt = f"""
    create cart:
A cart consists of the products that the buyer wants to purchase. To create the cart go through the conversation below
and create a list of tuples of product X quantity, e.g. [("product1", quantity1), ("product2", quantity2), ...] where products
are the products that the buyer has asked to buy or add to their cart and quantity is an integer.
{context}
cart: {current_cart}
{last_seller_utt}
{cnv_obj.turns[-1]}
cart:"""
    return prompt


def handle_create_or_update_order_cart(cnv_obj=None, merchant_id=None, current_cart=None, predict_fn=None, **kwargs):
    product_input = create_input_cart_mentions(cnv_obj, current_cart)
    model_predicted_cart = ast.literal_eval(predict_fn(product_input)[0])
    logger.info(f"Cart predicted by T5: {model_predicted_cart}")
    mentions = [t[0] for t in model_predicted_cart]
    products_from_history = list(set(match_mentions_to_products(merchant_id, mentions) + [t[0] for t in current_cart]))
    model_predicted_cart = generate_cart_mentions(cnv_obj, current_cart, products_from_history)
    logger.info(f"Cart predicted by chatgpt: {model_predicted_cart}")
    cart = [(d['product'], d['quantity']) for d in model_predicted_cart if 'product' in d]
    product_mentions = [d['product_mention'] for d in model_predicted_cart if 'product_mention' in d]
    if product_mentions:
        response = "\n".join([gen_disambiguation_response(merchant_id, product_mention) for product_mention in product_mentions])
    elif cart or current_cart:
        response = gen_cart_response(cart, [get_product_price(merchant_id, p) for p, _ in cart])
    else:
        response = gen_opening_response()
    return {
        'cart': cart,
        'response': response,
        'model_predicted_cart': model_predicted_cart
    }
