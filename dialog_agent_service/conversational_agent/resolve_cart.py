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
from dialog_agent_service.das_exceptions import ProductResolutionFailure
from typing import List
import re

ProductResponseUnion = namedtuple(
    'ProductResponseUnion', ['products', 'response'],
)
FUZZY_MATCH_THRESHOLD = 85

logger = logging.getLogger(__name__)


# ToDo: not ideal, replace later

with open(f'{constants.ROOT_DIR}/test_data/products_variants_prices.json') as f:
    VARIANTS_OBJ = json.load(f)
    logger.info('loaded product variants and prices!')

product_price_map = {
    merchant_id: {(product + ' - ' + variant): price
                  for product, d1 in d.items() for variant, price in d1.items()}
    for merchant_id, d in VARIANTS_OBJ.items()
}


class MatchType(Enum):
    EXACT = 1
    DISAMBIGUATE = 2


def match_mentions_to_products(merchant_id, mentions: List, limit=10):
    return list({tup[0]
            for mention in mentions
            for tup in
            process.extract(mention, product_price_map[merchant_id].keys(), scorer=fuzz.token_set_ratio, limit=limit)})


def get_product_price(merchant_id, product_name):
    product_match, _ = process.extract(product_name, product_price_map[merchant_id].keys(), scorer=fuzz.token_set_ratio, limit=1)[0]
    return product_price_map[merchant_id][product_match]


def get_matches(query, string_list, sim_fn, threshold):
    matches = process.extract(query, string_list, scorer=sim_fn)
    logger.info(f"query: {query}, matches: {matches}")
    exact_matches = [tup[0] for tup in matches if tup[1] == 100]
    if exact_matches and len(exact_matches) == 1:
        return exact_matches, [tup[0] for tup in matches[:3]]
    return [
               tup[0]
               for tup in matches
               if tup[1] > threshold], [tup[0] for tup in matches[:3]]


def custom_match(query, string_list):
    matches, all_matches = get_matches(query, string_list, fuzz.token_set_ratio, FUZZY_MATCH_THRESHOLD)
    if not matches:
        return MatchType.DISAMBIGUATE, all_matches[:4], all_matches
    return MatchType.DISAMBIGUATE if len(matches) != 1 else MatchType.EXACT, matches, all_matches


def gen_disambiguation_response(merchant_id: str, product_name: str) -> str:
    merchant_id = str(merchant_id)
    match_type, matches, all_matches = custom_match(product_name, VARIANTS_OBJ[merchant_id].keys())
    if match_type == MatchType.DISAMBIGUATE:
        """
        No matches with a high enough confidence. We disambiguate.
        """
        logger.debug(
            f'{product_name} search did not return a confident match',
        )
        return gen_non_specific_product_response(
            product_name, matches,
        )
    else:
        """
        Confident matches
        """
        products = []
        for product_match in matches:
            variants_dict = VARIANTS_OBJ[merchant_id][product_match]
            if len(variants_dict) == 1:
                # We assume that if the match was exact, LLM should have found it. So, we should not get to this part.'''
                return gen_non_specific_product_response(product_name, all_matches)
            else:
                return gen_variant_selection_response(
                    product_match, variants_dict
                )


def product_variant_to_product_name(merchant_id, product_variant_name):
    for i in re.finditer('-', product_variant_name):
        product_name = product_variant_name[:i.start()].strip()
        if product_name in VARIANTS_OBJ[merchant_id]:
            return product_name
    raise ProductResolutionFailure(f"Unable to find product name for {product_variant_name} from product dictionary")


def gen_disambiguation_response_llm(merchant_id, product_variant_name):
    merchant_id = str(merchant_id)
    product_variant_list = [s.strip() for s in product_variant_name.split('||')]
    product_names = list({product_variant_to_product_name(merchant_id, name) for name in product_variant_list})
    if len(product_names) == 1:
        return gen_variant_selection_response(product_names[0], VARIANTS_OBJ[merchant_id][product_names[0]])
    return gen_non_specific_product_response(product_names)
