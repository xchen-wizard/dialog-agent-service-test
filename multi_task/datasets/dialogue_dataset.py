from __future__ import annotations

import datetime

import torch
from simulator.data_utils import get_conversations_by_vendor


class DialogueDataset(torch.utils.data.Dataset):
    def __init__(self, tokenizer, vendors, task_pred_fn=None, skip_tasks={}, max_response_length=128):
        tokenizer.truncation_direction = 'left'
        self.max_response_length = max_response_length
        self.tokenizer = tokenizer
        self.conversations = []
        self.prefix_tok, self.prefix_tok_len = dict(), dict()
        self.data_points = []
        i = 0
        for vendor in vendors:
            conversations = get_conversations_by_vendor(
                vendor, min_turns=3, st=str(datetime.date.today()-datetime.timedelta(days=30)), turn_limit=5000,
            )
            self.prefix_tok[vendor] = tokenizer(
                f'{vendor} response: ', add_special_tokens=False).input_ids
            self.prefix_tok_len[vendor] = len(self.prefix_tok)
            for conversation in conversations:
                text = ''
                add = False
                for j, turn in enumerate(conversation.turns):
                    if turn.direction == 'outbound':
                        if j > 0 and task_pred_fn(text) not in skip_tasks:
                            self.data_points.append((vendor, i, j))
                            add = True
                        text += f'Seller: {turn.formatted_text}\n'
                    else:
                        text += f'Buyer: {turn.formatted_text}\n'
                if add:
                    self.conversations.append(conversation)
                    i += 1
        self.n_data_points = len(self.data_points)
        print(
            f'Dialogue dataset initialized with {self.n_data_points} data points')

    def __getitem__(self, idx):
        vendor, i, j = self.data_points[idx]
        input_text = '\n'.join(
            [f"{'Seller: ' if turn.direction == 'outbound' else 'Buyer: '}{turn.formatted_text}" for turn in self.conversations[i].turns[:j]])
        input_text += '\nSeller: '
        label = self.conversations[i].turns[j].text[0][1]
        input_ids = self.prefix_tok[vendor] + self.tokenizer(
            input_text, truncation=True, max_length=self.tokenizer.model_max_length-self.prefix_tok_len[vendor]).input_ids
        labels = self.tokenizer(label, truncation=True,
                                max_length=self.max_response_length).input_ids
        return {'input_ids': input_ids, 'labels': labels}

    def __len__(self):
        return self.n_data_points
