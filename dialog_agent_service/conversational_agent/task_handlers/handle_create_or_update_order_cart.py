import ast
import os
from typing import Tuple, List
from fuzzywuzzy import process, fuzz
from dialog_agent_service.utils.cart_utils import active_cart_to_virtual_cart
from ..chatgpt import generate_cart_mentions
from ..resolve_cart import gen_disambiguation_response_llm, match_mentions_to_products, get_product_price, is_multi_variant, product_variant_to_product_name
from ..response import gen_cart_response, gen_opening_response
from dialog_agent_service.utils.utils import handler_to_task_name
from dialog_agent_service.das_exceptions import CXCreatedCartException, MultipleVariantsInCart
import logging
logger = logging.getLogger(__name__)


def create_input_cart_mentions(cnv_obj, current_cart):
    context = "\n".join([str(t) for t in cnv_obj.turns[:-2]]
                        ) if cnv_obj.n_turns > 2 else ""
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
    task = handler_to_task_name()

    if 'staffId' in current_cart and current_cart['staffId'] is not None and current_cart['staffId'] != int(os.getenv('DAS_BOT_ID')):
        raise CXCreatedCartException(
            'Attempting to update a cart that was created by CX')

    _, _, virtual_cart = active_cart_to_virtual_cart(current_cart)
    logger.debug(f"Current Cart: {virtual_cart}")

    product_input = create_input_cart_mentions(cnv_obj, virtual_cart)
    cart_prediction = predict_fn(product_input)[0]
    try:
        model_predicted_cart = ast.literal_eval(cart_prediction)
        logger.info(f"Cart predicted by T5: {model_predicted_cart}")
        mentions = [t[0] for t in model_predicted_cart]
    except Exception as e:
        logger.exception(f"Parsing of Cart Prediction by T5 failed: {e}")
        mentions = [cart_prediction]
    products_from_history = list(set(match_mentions_to_products(
        merchant_id, mentions) + [t[0] for t in virtual_cart]))
    model_predicted_cart = generate_cart_mentions(
        cnv_obj, virtual_cart, products_from_history)
    logger.info(f"Cart predicted by chatgpt: {model_predicted_cart}")
    cart = [tup for tup in model_predicted_cart if '||' not in tup[0]]
    check_multi_variants_in_cart(cart, virtual_cart, mentions, merchant_id)  # Temporary fix to avoid GPT adding multi-variant items to cart unless user means it
    ambiguous_products = [tup[0]
                          for tup in model_predicted_cart if '||' in tup[0]]
    if ambiguous_products:
        response = "\n".join([gen_disambiguation_response_llm(
            merchant_id, product) for product in ambiguous_products])
    elif cart or virtual_cart:
        response = gen_cart_response(
            cart, [get_product_price(merchant_id, p) for p, _ in cart])
    else:
        response = gen_opening_response()
    return {
        'task': task,
        'cart': cart,
        'response': response,
        'model_predicted_cart': model_predicted_cart
    }


def check_multi_variants_in_cart(cart: List[Tuple[str, int]], last_cart: List[Tuple[str, int]], mentions: List, merchant_id):
    product_names = [t[0].split('-')[0].strip() for t in cart]
    if len(set(product_names)) != len(product_names):
        raise MultipleVariantsInCart("We are currently disallowing multiple variants of the same product in cart")

    """
    The section below tries to avoid adding multi-variant items to the cart
    unless we are confident. We use T5 prediction to see if the customer actually specified the variant
    or the LLM hallucinated and picked a variant by itself.
    """
    last_cart_products = {t[0] for t in last_cart}
    new_cart_products = [t[0] for t in cart if t not in last_cart_products]
    multi_variants_added = [p for p in new_cart_products if is_multi_variant(merchant_id, p)]
    for product_variant_name in multi_variants_added:
        closest_mention = process.extract(product_variant_name, mentions, scorer=fuzz.token_set_ratio, limit=1)[0][0]
        product_name = product_variant_to_product_name(merchant_id, product_variant_name)
        # if the closest mention contains the product name then we assume customer specified it
        if f"{product_name} -" in closest_mention:
            continue
        sim_to_product = fuzz.token_sort_ratio(closest_mention, product_name)
        sim_to_variant = fuzz.token_sort_ratio(closest_mention, product_variant_name)
        if sim_to_product >= sim_to_variant:

            logger.info(f"{product_variant_name} not added to cart since the closest mention {closest_mention} was not close enough: {sim_to_product} >= {sim_to_variant}")
            raise MultipleVariantsInCart(f"Not able to confidently add {product_variant_name} to cart")


