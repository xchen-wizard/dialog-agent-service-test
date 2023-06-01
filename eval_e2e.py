from __future__ import annotations

import asyncio
import logging
import os
import time

import pandas as pd

from dialog_agent_service.conversational_agent.conversation_utils import run_inference

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
file_handler = logging.FileHandler('goatful_test_2.log')
stream_handler = logging.StreamHandler()
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

BATCH_SIZE = 3
VENDOR_NAME = 'G.O.A.T. Fuel'
MERCHANT_ID = '29'
PROJECT_ID = 'stage-us-334018'
ENDPOINT_ID = '3705940482'


async def batch_process(batch_data: list[str]):
    return await asyncio.gather(
        *[
            run_inference(
                docs=[('inbound', msg)],
                vendor_name=VENDOR_NAME,
                merchant_id=MERCHANT_ID,
                project_id=PROJECT_ID,
                endpoint_id=ENDPOINT_ID,
            ) for msg in batch_data
        ],
    )


if __name__ == '__main__':
    # load data
    dfs = pd.read_excel('/Users/xchen/data/G.O.A.T. Fuel - Sample Questions.xlsx',
                        sheet_name=None, names=['query'], header=None)
    for sheet_name in dfs:
        # if sheet_name not in ('FAQ - Not Covered', 'Handoff Cases', 'Common Policy Questions', 'Common Beverage Questions', 'ProductQA - Covered', 'ProductQA - Not Covered'):
        #     continue
        logger.info(f'Sheet {sheet_name}')
        dfs[sheet_name] = dfs[sheet_name][(~dfs[sheet_name]['query'].isna()) & (
            dfs[sheet_name]['query'].str.strip() != '')]
        messages = dfs[sheet_name]['query'].tolist()
        logger.info(f'messages: {len(messages)}')
        i = 0
        response_objs = []
        try:
            while i < len(messages):
                logger.info(f'Batch = {i}: {i+BATCH_SIZE}')
                batch_data = messages[i: i+BATCH_SIZE]
                start = time.time()
                responses = asyncio.run(batch_process(batch_data))
                end = time.time()
                i += BATCH_SIZE
                logger.info(f'batch size of {BATCH_SIZE} took {end-start}s')
                response_objs.extend(responses)
            dfs[sheet_name]['response_obj'] = response_objs
            # we save each file individually
            dfs[sheet_name].to_json(
                '-'.join([VENDOR_NAME, sheet_name]), lines=True, orient='records')
        except Exception as e:
            logger.error(e)
            import pdb
            pdb.set_trace()

    row_count = 0
    new_dfs = []
    for sheet_name in dfs:
        df = dfs[sheet_name]
        logger.info(df.shape)
        row_count += df.shape[0]
        df['task'] = df.response_obj.apply(lambda x: x.get('task', ''))
        df['response'] = df.response_obj.apply(lambda x: x.get('response', ''))
        df['query_type'] = '-'.join([VENDOR_NAME, sheet_name])
        new_dfs.append(df[['query_type', 'query', 'task', 'response']])

    pd.concat(new_dfs).to_csv(
        'goatfule_sample_questions_responses_v2.csv', index=False)
    logger.info(f'row count: {row_count}')
