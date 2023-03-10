from __future__ import annotations

from random import sample

import numpy as np

from multi_task.data_readers.data_reader import DataReader


class UnsupervisedMLMDataReader(DataReader):
    """
    We assume that file has different paragraphs of interest separated by blank lines.
    This assumption is for simplicity and can be changed in future.
    Every paragraph is treated as a separate unit of knowledge ane masked separately.
    """

    def __init__(self, file: str, vendor, tokenizer):
        """
        store all the paragraphs into a list
        :param file:
        """
        self.noise_density = 0.15
        self.mean_noise_span_length = 3
        self.vendor = vendor
        self.tokenizer = tokenizer
        self.prefix = f'{vendor}: '
        self.prefix_tok = self.tokenizer(
            self.prefix, add_special_tokens=False).input_ids
        curr_para = []
        self.paragraphs = []
        self.qa = []

        def _append(para):
            if not para:
                return
            if para[0][-1] == '?':
                self.qa.append((para[0], '\n'.join(para[1:])))
            else:
                self.paragraphs.append('\n'.join(para))

        with open(file) as f:
            for line in f:
                line = line.strip()
                if len(line) > 0:
                    curr_para.append(line)
                else:
                    _append(curr_para)
                    curr_para = []
            _append(curr_para)

        self.n_para = len(self.paragraphs)
        self.n_qa = len(self.qa)
        self.frac_para = self.n_para/(self.n_para + self.n_qa)

    def sample(self, n):
        """
        sample n paragraphs
        mask each paragraph to create input and label
        See <https://arxiv.org/pdf/1910.10683.pdf> for details
        """
        para_sample_size = int(self.frac_para*n)
        qa_sample_size = n - para_sample_size

        qa_inputs = sample(self.qa, min(qa_sample_size, self.n_qa))
        qa_input_sample = self.tokenizer(
            [f'{self.vendor} response: Buyer: {x[0]}\nSeller: ' for x in qa_inputs]).input_ids
        qa_label_sample = self.tokenizer([x[1] for x in qa_inputs]).input_ids

        para_inputs = sample(self.paragraphs, min(n, self.n_para))
        input_ids = self.tokenizer(
            para_inputs, add_special_tokens=False).input_ids

        mask_indices = [self.random_spans_noise_mask(
            len(input_ids[i])) for i in range(para_sample_size)]
        labels_mask = [~l for l in mask_indices]

        input_ids_sentinel = [self.create_sentinel_ids(
            l.astype(np.int8)) for l in mask_indices]
        labels_sentinel = [self.create_sentinel_ids(
            l.astype(np.int8)) for l in labels_mask]

        para_input_sample = [self.prefix_tok + self.filter_input_ids(
            i, s) + [1] for i, s in zip(input_ids, input_ids_sentinel)]
        para_label_sample = [self.prefix_tok + self.filter_input_ids(
            i, s) + [1] for i, s in zip(input_ids, labels_sentinel)]

        return qa_input_sample + para_input_sample, qa_label_sample + para_label_sample

    def random_spans_noise_mask(self, length):
        """This function is adapted from `random_spans_helper <https://github.com/google-research/text-to-text-transfer-transformer/blob/84f8bcc14b5f2c03de51bd3587609ba8f6bbd1cd/t5/data/preprocessors.py#L2682>`__ .
        Noise mask consisting of random spans of noise tokens.
        The number of noise tokens and the number of noise spans and non-noise spans
        are determined deterministically as follows:
        num_noise_tokens = round(length * noise_density)
        num_nonnoise_spans = num_noise_spans = round(num_noise_tokens / mean_noise_span_length)
        Spans alternate between non-noise and noise, beginning with non-noise.
        Subject to the above restrictions, all masks are equally likely.
        Args:
            length: an int32 scalar (length of the incoming token sequence)
        Returns:
            a boolean tensor with shape [length]
        """
        orig_length = length

        num_noise_tokens = int(np.round(length * self.noise_density))
        # avoid degeneracy by ensuring positive numbers of noise and nonnoise tokens.
        num_noise_tokens = min(max(num_noise_tokens, 1), length - 1)
        num_noise_spans = int(
            np.round(num_noise_tokens / self.mean_noise_span_length))

        # avoid degeneracy by ensuring positive number of noise spans
        num_noise_spans = max(num_noise_spans, 1)
        num_nonnoise_tokens = length - num_noise_tokens

        # pick the lengths of the noise spans and the non-noise spans
        def _random_segmentation(num_items, num_segments):
            """Partition a sequence of items randomly into non-empty segments.
            Args:
                num_items: an integer scalar > 0
                num_segments: an integer scalar in [1, num_items]
            Returns:
                a Tensor with shape [num_segments] containing positive integers that add
                up to num_items
            """
            mask_indices = np.arange(num_items - 1) < (num_segments - 1)
            np.random.shuffle(mask_indices)
            first_in_segment = np.pad(mask_indices, [[1, 0]])
            segment_id = np.cumsum(first_in_segment)
            # count length of sub segments assuming that list is sorted
            _, segment_length = np.unique(segment_id, return_counts=True)
            return segment_length

        noise_span_lengths = _random_segmentation(
            num_noise_tokens, num_noise_spans)
        nonnoise_span_lengths = _random_segmentation(
            num_nonnoise_tokens, num_noise_spans)

        interleaved_span_lengths = np.reshape(
            np.stack([nonnoise_span_lengths, noise_span_lengths],
                     axis=1), [num_noise_spans * 2],
        )
        span_starts = np.cumsum(interleaved_span_lengths)[:-1]
        span_start_indicator = np.zeros((length,), dtype=np.int8)
        span_start_indicator[span_starts] = True
        span_num = np.cumsum(span_start_indicator)
        is_noise = np.equal(span_num % 2, 1)
        return is_noise[:orig_length]

    def create_sentinel_ids(self, mask_indices):
        """
        Sentinel ids creation given the indices that should be masked.
        The start indices of each mask are replaced by the sentinel ids in increasing
        order. Consecutive mask indices to be deleted are replaced with `-1`.
        """
        start_indices = mask_indices - \
            np.roll(mask_indices, 1, axis=-1) * mask_indices
        start_indices[0] = mask_indices[0]

        sentinel_ids = np.where(start_indices != 0, np.cumsum(
            start_indices, axis=-1), start_indices)
        sentinel_ids = np.where(
            sentinel_ids != 0, (len(self.tokenizer) - sentinel_ids), 0)
        sentinel_ids -= mask_indices - start_indices

        return sentinel_ids

    def filter_input_ids(self, input_ids, sentinel_ids):
        """
        Puts sentinel mask on `input_ids` and fuse consecutive mask tokens into a single mask token by deleting.
        This will reduce the sequence length from `expanded_inputs_length` to `input_length`.
        """
        return [x if y == 0 else y for x, y in zip(input_ids, sentinel_ids) if y >= 0]
