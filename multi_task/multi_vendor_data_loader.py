from __future__ import annotations

import torch
from data_readers.dialogue_reader import DialogueReader
from data_readers.dst_reader import DSTReader
from data_readers.unsupervised_mlm_data_reader import UnsupervisedMLMDataReader
from torch.nn.utils.rnn import pad_sequence


class MultiVendorDataLoader:
    """
    loads data across multiple vendors and generates batch for training
    """

    def __init__(self, data_dir: str, tokenizer, vendors):
        """
        expects the files in following format
        data_dir
            - task_descriptions.txt
            - vendor1
                - fact_sheet.txt
                - sample_dialogue.txt
            - vendor2
            ......
            .......
        loads all the data sources
        :param data_dir: root data directory
        """
        #self.task_reader = UnsupervisedMLMDataReader(f"{data_dir}/task_descriptions.txt", "", tokenizer)
        self.vendor_data_readers = dict()
        for vendor in vendors:
            self.vendor_data_readers[vendor] = {
                'facts': UnsupervisedMLMDataReader(f'{data_dir}/{vendor}/fact_sheet.txt', vendor, tokenizer),
                'response': DialogueReader(vendor, tokenizer),
                # "dst": DSTReader(f"{data_dir}/{vendor}/sample_dialogue.txt", tokenizer)
            }

    def gen_batch(self, batch_size, task_pct=.03, response_pct=.5, fact_pct=.40, dst_pct=.1):
        """
        generates a batched tensor according to percentages specified
        """
        inputs, labels = [], []
        per_vendor_size = (1.0 - task_pct)*batch_size / \
            len(self.vendor_data_readers)
        fact_batch_size = int(per_vendor_size * fact_pct)
        response_batch_size = int(per_vendor_size * response_pct)
        dst_batch_size = int(per_vendor_size * dst_pct)
        for k, v in self.vendor_data_readers.items():
            if fact_batch_size:
                print(f'Sampling {fact_batch_size} from facts')
                inp, tgt = v['facts'].sample(fact_batch_size)
                inputs.extend(inp)
                labels.extend(tgt)

            if response_batch_size:
                print(f'Sampling {response_batch_size} from responses')
                inp, tgt = v['response'].sample(response_batch_size)
                inputs.extend(inp)
                labels.extend(tgt)

            # inp, tgt = v["dst"].sample(dst_batch_size)
            # inputs.extend(inp)
            # labels.extend(tgt)

        residual = batch_size - len(inputs)
        # inp, tgt = self.task_reader.sample(residual)
        # inputs.extend(inp)
        # labels.extend(tgt)
        device = torch.device('mps')
        return pad_sequence([torch.tensor(x, dtype=torch.long, device=device) for x in inputs], batch_first=True), pad_sequence([torch.tensor(x, dtype=torch.long, device=device) for x in labels], batch_first=True, padding_value=-100)
