import ast
from ..chatgpt import generate_cart_mentions
from ..resolve_cart import resolve_cart, match_mentions_to_products,  NoMatchException
from .handle_recommend_product import handle_recommend_product
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
    logger.info(f"T5 prompt for cart: {prompt}")
    return prompt


def handle_create_or_update_order_cart(cnv_obj=None, merchant_id=None, current_cart=None, predict_fn=None, **kwargs):
    product_input = create_input_cart_mentions(cnv_obj, current_cart)
    model_predicted_cart = ast.literal_eval(predict_fn(product_input)[0])
    logger.info(f"Cart predicted by T5: {model_predicted_cart}")
    mentions = [t[0] for t in model_predicted_cart]
    products_from_history = list(set(match_mentions_to_products(merchant_id, mentions) + [t[0] for t in current_cart]))
    model_predicted_cart = generate_cart_mentions(cnv_obj, current_cart, products_from_history)
    logger.info(f"Cart predicted by chatgpt: {model_predicted_cart}")
    try:
        cart, response = resolve_cart(merchant_id, model_predicted_cart)
    except NoMatchException:
        # In case of no matches we use recommendation handler to find a suitable match
        return handle_recommend_product(cnv_obj, merchant_id, kwargs['vendor'])

    return {
        'cart': cart,
        'response': response,
        'model_predicted_cart': model_predicted_cart
    }
