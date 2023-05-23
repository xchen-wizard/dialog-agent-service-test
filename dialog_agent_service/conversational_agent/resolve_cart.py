from collections import namedtuple
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from Levenshtein import distance
from enum import Enum
import json
import logging
import os
from dialog_agent_service.conversational_agent.response import gen_cart_response
from dialog_agent_service.conversational_agent.response import gen_non_specific_product_response
from dialog_agent_service.conversational_agent.response import gen_variant_selection_response
from dialog_agent_service.conversational_agent.response import gen_opening_response
from dialog_agent_service import constants

ProductResponseUnion = namedtuple(
    'ProductResponseUnion', ['products', 'response'],
)
FUZZY_MATCH_THRESHOLD = 85

logger = logging.getLogger(__name__)

# ToDo: not ideal, replace later

with open(f'{constants.ROOT_DIR}/test_data/products_variants_prices.json') as f:
    VARIANTS_OBJ = json.load(f)
    logger.info('loaded product variants and prices!')


class MatchType(Enum):
    EXACT = 1
    DISAMBIGUATE = 2


def get_matches(query, string_list, sim_fn, threshold, prefer_exact=False):
    matches = process.extract(query, string_list, scorer=sim_fn)
    logger.info(f"query: {query}, matches: {matches}")
    exact_matches = [tup[0] for tup in matches if tup[1] == 100]
    if exact_matches and len(exact_matches) == 1:
        return exact_matches
    return [
        tup[0]
        for tup in matches
        if tup[1] > threshold]


def custom_match(query, string_list):
    matches = get_matches(query, string_list, fuzz.token_set_ratio, FUZZY_MATCH_THRESHOLD)
    return MatchType.DISAMBIGUATE if len(matches) != 1 else MatchType.EXACT, matches


def resolve_cart(merchant_id: str, cart: list[tuple[str, int]]):
    if not cart:
        return [], gen_opening_response()
    resolved_cart = []
    response = ""
    for product, qty in cart:
        products, product_response = match_product_variant(
            merchant_id, product,
        )
        if products:
            resolved_cart.extend([(p[0], p[1], qty) for p in products])
        if product_response:
            response += '\n' + product_response
    # TODO: Cart summary will be enabled only after backend integration
    if not response:
        response = gen_cart_response(
            resolved_cart,
        ) + '\n' + response
    return [(name, qty) for (name, _, qty) in resolved_cart], response


def match_product_variant(merchant_id: str, product_name: str) -> ProductResponseUnion:
    merchant_id = str(merchant_id)
    match_type, matches = custom_match(product_name, VARIANTS_OBJ[merchant_id].keys())
    if match_type == MatchType.DISAMBIGUATE:
        """
        No matches with a high enough confidence. We disambiguate.
        """
        logger.debug(
            f'{product_name} search did not return a confident match',
        )
        return ProductResponseUnion(
            None, gen_non_specific_product_response(
                product_name, matches,
            ),
        )
    else:
        """
        Confident matches
        """
        products = []
        response = ''
        for product_match in matches:
            variants_dict = VARIANTS_OBJ[merchant_id][product_match]
            if len(variants_dict) == 1:
                products.append(
                    (product_match + ' - ' + min(variants_dict.keys()), min(variants_dict.values()))
                )
            else:
                variant_matches = get_matches(
                    product_name,
                    [product_match + ' - ' + variant for variant in variants_dict.keys()],
                    fuzz.token_set_ratio,
                    FUZZY_MATCH_THRESHOLD,
                    prefer_exact=True
                )
                if variant_matches and len(variant_matches) == 1:
                    full_name = variant_matches[0]
                    variant_name = full_name.split(" - ")[
                        -1].strip()  # TODO: This is potentially problematic if the variant name has hyphen in it
                    products.append((full_name, variants_dict[variant_name]))
                else:
                    response += '\n' + gen_variant_selection_response(
                        product_match, variants_dict,
                    )

        return ProductResponseUnion(products, response)

