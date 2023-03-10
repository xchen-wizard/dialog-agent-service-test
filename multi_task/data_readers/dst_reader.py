from __future__ import annotations

import json
import random

from .data_reader import DataReader


class DSTReader(DataReader):
    """
    reads a dialogue annotated with dialogue state tracking
    and creates data points for task and slots
    """

    def __init__(self, file, tokenizer):
        self.prefix = 'question answering: '
        self.prefix_tok = tokenizer(
            self.prefix, add_special_tokens=False).input_ids
        self.prefix_tok_len = len(self.prefix_tok)
        inputs, targets = [], []
        with open(file) as f:
            lines = f.readlines()
        for i, l in enumerate(lines):
            if l.startswith('State:'):
                past_dialogue = '\n'.join(
                    line for line in lines[:i] if not line.startswith('State:'))
                input_task = f"""
                {past_dialogue}

                Which of the following tasks does the buyer want us to do right now:
                - PlaceOrder
                - RecommendProduct
                - UpdateAccountDetails
                - AnswerQuestionAboutProduct
                - AnswerQuestionAboutService
                - AnswerQuestionAboutSeller
                - ResolveOrderIssue
                - GiveOrderStatus
                - CancelOrder
                - ReturnOrder
                - None
                """
                inputs.append(input_task)
                state = json.loads(l[6:].strip())
                task = state['task']
                targets.append(task)

                slots = state.get('slots', dict())
                if 'cart' in slots:
                    input_products = f"""
                    {past_dialogue}

                    Write a comma separated list of products the buyer is interested in purchasing.
                    """
                    inputs.append(input_products)
                    targets.append(', '.join([x[0] for x in slots['cart']]))
                    for product, qty in slots['cart']:
                        input_qty = f"""
                        {past_dialogue}

                        How many of {product} is the buyer interested in purchasing?
                        """
                        inputs.append(input_qty)
                        targets.append(qty)
        suffix_encodings = tokenizer(inputs, add_special_tokens=False, truncation=True,
                                     max_length=tokenizer.model_max_length-self.prefix_tok_len-1).input_ids
        self.encodings = [self.prefix_tok + t + [1] for t in suffix_encodings]
        self.labels = tokenizer(targets, truncation=True).input_ids
        self.tokenizer = tokenizer
        self.samples = len(self.encodings)

    def sample(self, n):
        samples_idx = random.sample(range(self.samples), n)
        return [self.encodings[i] for i in samples_idx], [self.labels[i] for i in samples_idx]
