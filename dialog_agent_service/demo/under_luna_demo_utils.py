import os
import re
import sys
import openai
import tiktoken
from nltk.tokenize import sent_tokenize
import configparser
from elasticsearch import Elasticsearch


from dialog_agent_service.conversational_agent.conversation_utils import encode_sentence
from dialog_agent_service.db import get_mysql_cnx_cursor


ENDPOINT_ID = os.getenv('ST_VERTEX_AI_ENDPOINT_ID', '3363709534576050176')
PROJECT_ID = os.getenv('VERTEX_AI_PROJECT_ID', '105526547909')

openai.api_key = os.getenv('OPENAI_API_KEY')

messages = []


def index_demo_helper(es_client, dimensions: int):
    index = 'underluna-demo'

    es_client.indices.delete(index=index, ignore=[404])

    es_index_body = es_index_body = {
      "mappings": {
        "properties": {
          "question": {
            "type": "text"
          },
          "answer": {
            "type": "text"
          },
          "question_vector": {
            "type": "dense_vector",
            "dims": dimensions
          }
        }
      }
    }

    es_client.indices.create(index=index, body=es_index_body)

    populate_demo_indices(es_client, index)


def populate_demo_indices(es_client, index: str):
    faqs = get_demo_faqs()
    txt_faqs = {} # get_txt_demo_faqs()

    for question in faqs:
      embedding = encode_sentence(question, PROJECT_ID, ENDPOINT_ID)

      es_data = {
        "question": question,
        "answer": faqs[question],
        "question_vector": embedding
      }

      es_client.index(index=index, document=es_data)

    for question in txt_faqs:
      embedding = encode_sentence(question, PROJECT_ID, ENDPOINT_ID)

      es_data = {
        "question": question,
        "answer": faqs[question],
        "question_vector": embedding
      }

      es_client.index(index=index, document=es_data)


def get_demo_faqs():
  faq_query = """
  SELECT 
    q.text AS question,
    a.text AS answer
  FROM
    faqs q
  JOIN
    faqs a
  ON 
    q.answerId = a.id
  WHERE
    q.merchantId = '53' AND (q.type = 'question' OR q.type = 'questionExpansion' OR q.type = 'questionExtraction')
  """

  with get_mysql_cnx_cursor() as cursor:
      cursor.execute(faq_query)
      data = cursor.fetchall()

  faqs = {}

  for faq in data:
     faqs[faq['question']] = faq['answer']

  return faqs


def get_txt_demo_faqs():
  faqs = {}
   
  lines = open("./under_luna_data/under_luna_faq.txt","r").readlines()
  for i,lx in enumerate(lines):
      lx = lx.strip()
      part = lx.partition(":")
      if part[0] != 'Question' and part[0] != 'Answer':
          print("Error in line {}: {} ({})".format(i,lx,part[0]))
          sys.exit()
      elif part[0] == 'Question':
          question = part[2]
      elif part[0] == "Answer":
          faqs[question] = part[2]
   
  return faqs


def faq_demo_search(es_cleint, question: str):
  index = 'underluna-demo'

  question_embedding = encode_sentence(question, PROJECT_ID, ENDPOINT_ID)

  sem_search = None
  sem_search = es_cleint.search(index=index, body={
    "query": {
        "script_score": {
            "query": {
                "match_all": {}
            },
            "script": {
                "source": "cosineSimilarity(params.queryVector, 'question_vector') + 1.0",
                "params": {
                    "queryVector": question_embedding
                }
            }
        }
    }
  })
  if sem_search['hits']['hits'] != []:
    if (sem_search['hits']['hits'][0]['_score']) > 0:
        for hit in sem_search['hits']['hits'][0:1]:
            top_question = hit['_source']['question'].strip('\n')
            top_answer = hit['_source']['answer'].strip('\n')
            break
        sem_search = (top_question, top_answer)
    else:
        sem_search = None
  else:
    sem_search = None
  return sem_search


def fill_msg_and_send(filler):
    global messages

    msize = num_tokens_from_messages(messages)
    # print("messages size (in): {}".format(msize))
    if msize > 3300:
        messages = [messages[0],messages[1]]

    messages.append(
        {"role": "user",
         "content": filler},
    )
    msize = num_tokens_from_messages(messages)

    try:
        chat = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=messages
        )
        reply = chat.choices[0].message.content
    except Exception as e:
        reply = str(e)
      
    # Only keep first sentence, not all the explanation after that
    # reply = reply.rstrip('\n')
    # reply1st = sent_tokenize(reply)[0]
    messages.append(
        {"role": "assistant", "content": reply},
    )
    return reply


def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
  """Returns the number of tokens used by a list of messages."""
  try:
    encoding = tiktoken.encoding_for_model(model)
  except KeyError:
    encoding = tiktoken.get_encoding("cl100k_base")
  if model == "gpt-3.5-turbo-0301":  # note: future models may deviate from this
    num_tokens = 0
    for message in messages:
      num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
      for key, value in message.items():
        num_tokens += len(encoding.encode(value))
        if key == "name":  # if there's a name, the role is omitted
          num_tokens += -1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens
  else:
    raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {model}.""")
  
  
def get_focus(filler):
    global messages
    prods = [
        "Unscented Shampoo",
        "Sweet Baby Orange Shampoo",
        "Warrior Shampoo",
        "Unscented Conditioner",
        "Luna Love Conditioner",
        "Serenity Conditioner",
        "Revive Conditioner",
    ]

    topic = None
    words = [x.lower() for x in filler.split(' ') ]
    messages.append(
        {"role": "user",
         "content": "Only if one of the named listed products is mentioned in this input: " + filler + ", then update the current topic and reply only with the mentioned product's actual name from this list as the current topic of the conversation:" + str(
             prods) + " otherwise reply with only the product name of the previous most recent topic, if any. Do not use any other words in your reply."}
    )
    try:
        chat = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=messages
        )
        reply = chat.choices[0].message.content
        topic = reply
        messages.append(
            {"role": "assistant", "content": reply},
        )
    except Exception as e:
        reply = str(e)

    return topic
  
  
def faq_demo(es_client, question: str):
  prompt = "combine this question/answer pair into a single clear consistent statement: <FILLERQ>, <FILLERA>."
  q1 = question
  focus = None

  if focus != None:
      if ' it ' in q1.lower() and focus != None:
          q1 = q1.replace(' it ',' ' + focus + ' ')
      if ' its ' in q1.lower() and focus != None:
          q1 = q1.replace(' its ', ' ' + focus + ' ')
      elif ' that ' in q1.lower() and focus != None:
          q1 = q1.replace(' that ',' ' + focus + ' ')
  # print("Focus = {}".format(focus))

  sem_search = faq_demo_search(es_client, q1)

  augmented_prompt = re.sub(r'<FILLERQ>',sem_search[0],prompt)
  augmented_prompt = re.sub(r'<FILLERA>',sem_search[1],augmented_prompt)

  answer = fill_msg_and_send(augmented_prompt)

  print("{}\t{}".format(question,answer))
  focus = get_focus(question+answer)

  return answer