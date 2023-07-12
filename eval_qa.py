#!/usr/bin/env python
# coding: utf-8



import mysql.connector.pooling
import os
import logging
import tqdm

logger = logging.getLogger()


# In[3]:


from dialog_agent_service import init_mysql_db


# In[4]:


mysql_pool = init_mysql_db()


# In[8]:


from dialog_agent_service.db import get_mysql_cnx_cursor

query = """
select fq.merchantId, fq.text as 'question', fa.text as 'answer' from faqs fq join faqs fa on fq.answerId = fa.id where fq.type = 'question'
"""
with get_mysql_cnx_cursor() as cursor:
    cursor.execute(query)
    data = cursor.fetchall()


# get merchantId to vendorName
query = """
select id, name from vendors
"""
with get_mysql_cnx_cursor() as cursor:
    cursor.execute(query)
    merchants = cursor.fetchall()


# In[24]:


id2merchant = {str(item['id']): item['name'] for item in merchants}



from dialog_agent_service.conversational_agent.task_handlers.handle_answer_miscellaneous_questions import handle_answer_miscellaneous_questions
from dialog_agent_service.conversational_agent.conversation_parser import Conversation



# ## single threaded requests

# In[25]:


queries = []
for item in data:
    convo = Conversation([('inbound', item['question'])])
    q_args = (convo, str(item['merchantId']), id2merchant[str(item['merchantId'])])
    queries.append(q_args)


# In[46]:


results = []
for idx, (convo, merchant_id, merchant_name) in tqdm.tqdm(enumerate(queries), total=len(queries)):
    rslt = {
        'merchant_id': merchant_id,
        'merchant_name': merchant_name,
        'question': str(convo),
        'ground_truth': data[idx]['answer']
    }
    
    try:
        resp = handle_answer_miscellaneous_questions(convo, merchant_id, merchant_name)
        rslt['bot_answer'] = resp.get('response')
    except Exception as e:
        print(idx, e)
    results.append(rslt)

import json
with open('qa_chatgpt_4.json', 'w') as f:
    json.dump(results, f)



