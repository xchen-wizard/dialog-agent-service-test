from __future__ import annotations

import datetime
from collections import Counter

from numpy import random
from simulator.data_utils import get_conversations_by_vendor
from utils.cluster_text import cluster_text

from .data_reader import DataReader


class DialogueReader(DataReader):
    """
    reads conversation history from data lake and creates each response
    as target based on conversation history as input
    """

    def __init__(self, vendor: str, tokenizer):
        self.conversations = get_conversations_by_vendor(vendor, min_turns=3, st=str(
            datetime.date.today()-datetime.timedelta(days=30)), turn_limit=1000)
        self.tokenizer = tokenizer
        self.prefix = f'{vendor} response: '
        self.prefix_tok = tokenizer(
            self.prefix, add_special_tokens=False).input_ids
        self.prefix_tok_len = len(self.prefix_tok)
        self.candidates_to_sample = [(i, j) for i, cnv in enumerate(
            self.conversations) for j, turn in enumerate(cnv.turns) if j != 0 and turn.direction == 'outbound']
        self.n_candidates = len(self.candidates_to_sample)
        cluster_labels = cluster_text(
            [self.conversations[i].turns[j].text[0][1] for i, j in self.candidates_to_sample])
        freq = Counter(cluster_labels)
        n_clusters = len(freq)
        self.sample_probs = [1.0/(n_clusters*freq[cluster_label])
                             for cluster_label in cluster_labels]

    def sample(self, n):
        """
        samples a conversation and then an outbound message
        """
        sample_turns_idx = random.choice(
            range(self.n_candidates), size=n, replace=False, p=self.sample_probs)
        sample_turns = [self.candidates_to_sample[i] for i in sample_turns_idx]
        self.sample_turns_tok = self.tokenizer([f'{self._render_past_turns(i, j)}\nSeller: ' for i, j in sample_turns],
                                               add_special_tokens=False, truncation=True, max_length=self.tokenizer.model_max_length-self.prefix_tok_len-1).input_ids
        return [self.prefix_tok + t + [1] for t in self.sample_turns_tok], self.tokenizer([self.conversations[i].turns[j].text[0][1] for i, j in sample_turns]).input_ids

    def _render_past_turns(self, i, j):
        return '\n'.join([f"{'Seller: ' if turn.direction == 'outbound' else 'Buyer: '}{turn.formatted_text}" for turn in self.conversations[i].turns[:j]])
