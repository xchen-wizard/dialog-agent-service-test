from __future__ import annotations

import glob
import json
import logging
from collections import namedtuple
import os
from typing import List
from typing import Tuple

from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from Levenshtein import distance
from enum import Enum

from .conversation_parser import Conversation
from .response import gen_cart_response
from .response import gen_non_specific_product_response
from .response import gen_variant_selection_response
from dialog_agent_service.db import get_merchant, merchant_semantic_search, product_search, product_semantic_search
from dialog_agent_service.search.SemanticSearch import SemanticSearch
from .chatgpt import product_qa, merchant_qa, recommend

max_conversation_chars_task = 600
max_conversation_chars_cart = 1500
max_conversation_chars_products = 1000
logger = logging.getLogger(__name__)

ProductResponseUnion = namedtuple(
    'ProductResponseUnion', ['products', 'response'],
)
FUZZY_MATCH_THRESHOLD = 85
LEVENSHTEIN_THRESHOLD = 90
MAX_CONVERSATION_CHARS = 600
FAQ_THRESHOLD = 1.6
# ToDo: not ideal, replace later
with open('../test_data/products_variants_prices.json') as f:
    VARIANTS_OBJ = json.load(f)
    logger.info('loaded product variants and prices!')

semantic_search_obj = SemanticSearch()


class MatchType(Enum):
    EXACT = 1
    DISAMBIGUATE = 2


def custom_sim(s1, s2):
    return int(100*(1.0 - distance(s1, s2, weights=(1, 0, 1), score_cutoff=20) / float(max(len(s1), len(s2)))))


def get_matches(query, string_list, sim_fn, threshold, prefer_exact=False):
    matches = process.extract(query, string_list, scorer=sim_fn)
    print(f"query: {query}, matches: {matches}")
    exact_matches = [tup[0] for tup in matches if tup[1]==100]
    if exact_matches and len(exact_matches) == 1:
        return exact_matches
    return [
        tup[0]
        for tup in matches
        if tup[1] > threshold]


def custom_match(query, string_list):
    matches = get_matches(query, string_list, custom_sim, LEVENSHTEIN_THRESHOLD)
    if matches:
        return MatchType.EXACT, matches
    matches = get_matches(query, string_list, fuzz.token_set_ratio, FUZZY_MATCH_THRESHOLD)
    return MatchType.DISAMBIGUATE if len(matches) != 1 else MatchType.EXACT, matches


class T5InferenceService:
    def __init__(self, data_dir, model_name=None, model_dir=None):
        """
        obj = T5InferenceService("google/flan-t5-xl", "model_dir", "test_data", ["Under Luna", "AAVRANI", "MYOS Pet"])
        :param model_name: pre-trained model name
        :param model_dir: model directory with finetuned model
        :param data_dir: directory with product sheet and example dialogues
        """
        if model_name is not None and model_dir is not None:
            from transformers import T5Tokenizer, T5ForConditionalGeneration
            self.tokenizer = T5Tokenizer.from_pretrained(model_name)
            self.model = T5ForConditionalGeneration.from_pretrained(model_dir)
        with open(f'{data_dir}/task_descriptions.txt') as f:
            logger.info(f'loading task_descriptions.txt from {data_dir}')
            self.task_descriptions = f.read()

    def predict(self, text):
        input = self.tokenizer(text, padding=True, return_tensors='pt')
        outputs = self.model.generate(**input, max_new_tokens=128)
        return self.tokenizer.batch_decode(outputs, skip_special_tokens=True)

    def infer(self, docs, vendor, merchant_id, predict_fn, task_routing_config: dict = {}):
        """
        :param conversation: Conversation formatted as follows:
        Seller: Are you interested in..
        Buyer: Yes
        Seller: Ok..
        Buyer: I had a question
        Note that it should always end with Buyer
        :return: dict with different outputs of interest
        """

        TASKS = ['CreateOrUpdateOrderCart', 'AnswerProductQuestions', 'AnswerSellerQuestions', 'RecommendProduct']
    
        for t in TASKS:
            if not task_routing_config.get(t):
                task_routing_config[t] = {'responseType': 'assisted'}

        merchant_id = str(merchant_id)
        cnv_obj = Conversation(docs)
        if cnv_obj.n_turns == 0:
            logger.error('Infer called with empty conversation. Aborting.')
            return dict()
        last_turn = cnv_obj.turns[-1]
        conversation = str(cnv_obj)
        logger.debug(f'Conversation Context: {conversation}')
        if last_turn.direction != 'inbound':
            logger.error(
                'Infer called after an outbound. Aborting. Please only call when the latest turn is inbound',
            )
            return dict()
        # first predict task
        input, _ = create_input_target_task(
            conversation, '', task_descriptions=self.task_descriptions,
        )
        task = predict_fn(input)[0]
        logger.info(f"Task Detected:{task}")
        logger.info(f"Task Routing Config:{task_routing_config}")
        response = ''
        cart = []
        model_predicted_cart = []
        source = 'model'
        is_suggested = True

        if task_routing_config[task]['responseType'] == 'cx':
            return {'task': task, 'suggested': False}

        if 'CreateOrUpdateOrderCart' in task:
            product_input, _ = create_input_target_cart(conversation, '')
            products = predict_fn(product_input)[0]
            if products != 'None':
                qty_input, _ = create_input_target_cart(
                    conversation, products + ';', qty_infer=True,
                )
                qty_list = predict_fn(qty_input)
                model_predicted_cart = list(zip(products.split(','), qty_list))
                for product, qty in model_predicted_cart:
                    if qty.isdigit():
                        cart.append((product, int(qty)))
                    else:
                        logger.error(
                            f'Quantity {qty} predicted for product {product} not of the right type. Skipping.',
                        )
                cart, response = resolve_cart(merchant_id, cart, response)

        conversation += 'Seller: '
        if 'AnswerProductQuestions' in task:
            product_input, _ = create_input_target_products(conversation, "")
            products = predict_fn(product_input)[0]
            logger.info(f"PRODUCT FUZZY-WUZZY SEARCH: {products}")
            context = ""
            for product in products.split(","):
                product_results = product_semantic_search(merchant_id, product)[
                    'productVariantSemanticSearch'][0:1]  # first result only
                logger.info(
                    f"PRODUCT:{product}: SEMANTIC SEARCH RESULTS: {product_results}")
                for pr in product_results:
                    context += format_product_result(pr)
                    context += "\n"

            logger.info(f"Prompt Context:{context}")

            conversation += "Seller: "
            llm_response = product_qa(cnv_obj, context, vendor)

            logger.info(f"LLM Response: {llm_response}")

            # TODO - check llm_response
            response += llm_response

        if 'AnswerSellerQuestions' in task:
            # First check FAQ: we give precedence to it
            # TODO: Disable FAQs for now, convert to policies
            # answer, score = None, 0.0
            # try:
            #     merchant_site_id = get_merchant(merchant_id)['site_id']
            #     answer, score = semantic_search_obj.faq_search(
            #         merchant_site_id, last_turn.formatted_text,
            #     )
            # except Exception as e:
            #     logger.error(f'Error querying ES: {e}')
            # if answer and score > FAQ_THRESHOLD:
            #     logger.info('FAQ DETECTED')
            #     response += answer
            #     source = 'faq'
            # else:
            merchant_query = last_turn.formatted_text
            merchant_results = merchant_semantic_search(merchant_id, merchant_query)[
                'merchantSemanticSearch'][0:10] #TODO - first 10 only
            logger.info(f"Query: {merchant_query}, merchantSemanticSearch results: {merchant_results}")
            
            context = ""
            for mr in merchant_results:
                context += format_merchant_results(mr)
                context += '\n'

            logger.info(f"Prompt Context:{context}")
            
            llm_response = merchant_qa(cnv_obj, context, vendor)
            logger.info(f"LLM Response: {llm_response}")

            # TODO - check llm_response
            response += llm_response

        if 'RecommendProduct' in task:
            product_query = last_turn.formatted_text
            product_results = product_semantic_search(merchant_id, product_query)[
                'productVariantSemanticSearch'][0:3]  # TODO: first 3 only
            logger.info(
                f"Query:{product_query}, productSemanticSearch results: {product_results}")

            context = ""
            for pr in product_results:
                context += format_product_result(pr)
                context += '\n'

            logger.info(f"Prompt Context:{context}")

            llm_response = recommend(cnv_obj, context, vendor)
            logger.info(f"LLM Response: {llm_response}")

            # TODO - check llm_response
            response += llm_response

        primary_task = task.split(",")[0]
        logger.info(f"Primary Task:{primary_task}")
        is_suggested = task_routing_config[primary_task]['responseType'] == 'assisted'
        ret_dict = {
            'task': task,
            'cart': cart,
            'model_predicted_cart': model_predicted_cart,
            'response': response,
            'source': source,
            'suggested': is_suggested
        }
        if not ret_dict['response']:
            del ret_dict['response']
        if not ret_dict['cart']:
            del ret_dict['cart']
        logger.debug(f'Returning json object: {ret_dict}')
        return ret_dict


def format_product_result(pr):
    output = ""
    display_name = pr.get("product", {}).get("name") + " - " + pr.get("name")
    desc = pr.get("description")
    output += f"product name is {display_name},"
    output += f"product description is {desc}"

    return output

def format_merchant_results(mr):
    output = ""
    policy_type = mr.get("policyType")
    policy_contents = mr.get("policyContents")
    output += policy_type + "\n"
    output += policy_contents + "\n"

    return output


def create_input_target_task(conversation, target_str, **kwargs):
    return [f"""
predict task based on task descriptions below:
{kwargs['task_descriptions']}
The below is an interaction between buyer and seller:
{conversation[-max_conversation_chars_task:]}
Write a comma separated list of tasks that the buyer wants us to do right now.
"""], [target_str]


def create_input_target_cart(conversation, target_str, **kwargs):
    inputs = [f"""
answer products of interest:
{conversation[-max_conversation_chars_cart:]}
Write a comma separated list of products that the buyer is interested in purchasing.
"""] if not kwargs.get('qty_infer', False) else []
    products_qty = target_str.split(';')
    products = products_qty[0].strip()
    targets = [products]
    if len(products_qty) > 1:
        targets.extend([s.strip() for s in products_qty[1].strip().split(',')])
        products = products.split(',')
        for product in products:
            inputs.append(
                f"""
answer product quantity:
{conversation[-max_conversation_chars_cart:]}
How many {product} does the buyer want?
                """,
            )
    return inputs, targets


def create_input_target_products(conversation, target_str, **kwargs):
    return [
        f"""
        products the question is about:
        The below is an interaction between buyer and seller at the end of which buyer has a question about some products.
        {conversation[-max_conversation_chars_products:]}
        Write a comma separated list of products that the buyer has question(s) on.
        """
    ], [target_str]


def resolve_cart(merchant_id: str, cart: list[tuple[str, int]], response: str):
    if not cart:
        return [], gen_opening_response()
    resolved_cart = []
    for product, qty in cart:
        products, product_response = match_product_variant(
            merchant_id, product,
        )
        if products:
            resolved_cart.extend([(p[0], p[1], qty) for p in products])
        if product_response:
            response += '\n' + product_response
    # TODO: Cart summary will be enabled only after backednd integration
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
