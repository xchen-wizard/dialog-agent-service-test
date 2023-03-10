from __future__ import annotations

from pathlib import Path
from typing import List

import torch


class DSTDataset(torch.utils.data.Dataset):
    def __init__(self, tokenizer, dialogues_dir_list: list[str], task_descriptions_file: str, label_prefixes=['task', 'cart'], max_conversation_len_chars=600):
        inputs, targets = [], []
        label_prefixes_len = [len(s) for s in label_prefixes]
        conversation = ''
        with open(task_descriptions_file) as f:
            task_descriptions = f.read()
        for dialogues_dir in dialogues_dir_list:
            paths = Path(dialogues_dir).glob('*.txt')
            for path in paths:
                with open(path) as f:
                    lines = f.readlines()
                for i, line in enumerate(lines):
                    input_line = True
                    for pfx, pfx_len in zip(label_prefixes, label_prefixes_len):
                        if line.startswith(pfx):
                            inputs.append(DSTDataset.create_input(
                                conversation[-max_conversation_len_chars:], label=pfx, task_descriptions=task_descriptions))
                            targets.append(line[pfx_len+1:].strip())
                            input_line = False
                            break
                    if input_line:
                        conversation += line
        self.encodings = tokenizer(inputs)
        self.labels = tokenizer(targets)['input_ids']

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx])
                for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)

    @classmethod
    def create_input(cls, conversation, label, **kwargs):
        fn = getattr(cls, f'create_input_{label}')
        return fn(conversation, **kwargs)

    @classmethod
    def create_input_task(cls, conversation, **kwargs):
        return f"""
question answering:
{kwargs['task_descriptions']}
The below is an interaction between buyer and seller:
{conversation}
Write a comma separated list of tasks that the buyer wants us to do right now.
"""

    @classmethod
    def create_input_cart(cls, conversation, **kwargs):
        return f"""
question answering:
{conversation}
Write a comma separated list of products that the buyer is interested in purchasing.
"""
