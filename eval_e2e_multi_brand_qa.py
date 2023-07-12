from __future__ import annotations

import asyncio
import logging
import os
import time

import pandas as pd
import json

from dialog_agent_service.conversational_agent.conversation_utils import run_inference
from dialog_agent_service.conversational_agent.conversation_parser import Conversation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
# file_handler = logging.FileHandler('goatful_test_2.log')
stream_handler = logging.StreamHandler()
# logger.addHandler(file_handler)
logger.addHandler(stream_handler)

BATCH_SIZE = 1
# VENDOR_NAME = 'G.O.A.T. Fuel'
# MERCHANT_ID = '29'
PROJECT_ID = 'stage-us-334018'
ENDPOINT_ID = '3705940482'


async def batch_process(batch_data: list[tuple]):
    return await asyncio.gather(
        *[
            run_inference(
                docs=msgs,
                vendor_name=vendor_name,
                merchant_id=vendor_id,
                project_id=PROJECT_ID,
                endpoint_id=ENDPOINT_ID,
            ) for msgs, vendor_name, vendor_id in batch_data
        ],
    )


def process_batch_data(batch_data: list[dict]) -> list[dict]:
    """
    batch_data is a list of tuples
    - input list of message dict {}
    - expected output list of message dict {}
    """
    batch_inputs = []
    batch_outputs = []
    for inputs,  outputs in batch_data:
        # merge inputs
        vendor_id = inputs[0].get('vendorId')
        vendor_name = inputs[0].get('vendorName')
        input_msgs = [(input.get('direction'), input.get('body')) for input in inputs]
        output_msg = "\n".join([output.get('body') for output in outputs])
        batch_inputs.append((input_msgs, vendor_name, vendor_id))
        batch_outputs.append(output_msg)
    assert len(batch_inputs) == len(batch_outputs)
    return batch_inputs, batch_outputs


if __name__ == '__main__':
    # load data
    with open('/Users/xchen/data/multibrand_qa_dataset_06-10-23_06-21-23.json') as f:
        data = json.load(f)
    logger.info(f'total data length: {len(data)}')
    i = 18
    response_objs = []
    inputs = []
    outputs = []
    try:
        while i < len(data):
            logger.info(f'Batch = {i}: {i+BATCH_SIZE}')
            batch_data = data[i: i+BATCH_SIZE]
            # batch_data = data[14: 15]
            # print(batch_data)
            batch_inputs, batch_outputs = process_batch_data(batch_data)
            start = time.time()
            responses = asyncio.run(batch_process(batch_inputs))
            end = time.time()
            i += BATCH_SIZE
            logger.info(f'batch size of {BATCH_SIZE} took {end-start}s')
            response_objs.extend(responses)
            inputs.extend(batch_inputs)
            outputs.extend(batch_outputs)
            # import pdb; pdb.set_trace()
            # break
        # creates a df
        df = pd.DataFrame([(Conversation(input_msgs), vendor_name, vendor_id) for input_msgs, vendor_name, vendor_id in inputs],
                          columns=['messages', 'vendorName', 'vendorId'])
        df['response_obj'] = response_objs
        df['task'] = df.response_obj.apply(lambda x: x.get('task', ''))
        df['response'] = df.response_obj.apply(lambda x: x.get('response', ''))
        df['docs'] = df.response_obj.apply(lambda x: x.get('docs', ''))
        df['expected_output'] = outputs

        df.to_csv('/Users/xchen/data/multibrand_qa_dataset_06-10-23_06-21-23-gpt3.5-0301-no-guardrails_02.csv')

    except Exception as e:
        logger.error(e)
        import pdb; pdb.set_trace()

    # row_count = 0
    # new_dfs = []
    # for sheet_name in dfs:
    #     df = dfs[sheet_name]
    #     logger.info(df.shape)
    #     row_count += df.shape[0]
    #     df['task'] = df.response_obj.apply(lambda x: x.get('task', ''))
    #     df['response'] = df.response_obj.apply(lambda x: x.get('response', ''))
    #     df['query_type'] = '-'.join([VENDOR_NAME, sheet_name])
    #     df['docs'] = df.response_obj.apply(lambda x: x.get('docs', ''))
    #     new_dfs.append(df[['query_type', 'query', 'task', 'response', 'docs']])
    #
    # pd.concat(new_dfs).to_csv(
    #     'goatfuel_sample_questions_responses_v3.csv', index=False)
    # logger.info(f'row count: {row_count}')
