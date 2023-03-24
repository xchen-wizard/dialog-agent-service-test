import os

from dialog_agent_service.conversational_agent.conversation_utils import encode_sentence, get_all_faqs, get_merchant_site_ids, get_all_variants
from dialog_agent_service.app_utils import logger
from dialog_agent_service.demo.under_luna_demo_utils import faq_demo, index_demo_helper

from elasticsearch import Elasticsearch
import logging

logger = logging.getLogger(__name__)

ENDPOINT_ID = os.getenv('ST_VERTEX_AI_ENDPOINT_ID', '3363709534576050176')
PROJECT_ID = os.getenv('VERTEX_AI_PROJECT_ID', '105526547909')


class SemanticSearch:
  def __init__(self, dimensions = 768, is_demo = False):
    self.dimensions = dimensions

    try: 
      if is_demo:
        self.client = Elasticsearch(
        cloud_id=os.environ.get('ES_DEMO_CLOUD_ID'),
        basic_auth=(os.environ.get('ES_DEMO_USER'), os.environ.get('ES_DEMO_PASSWORD'))
        )
      elif os.environ.get('_ENV') == 'production':
        self.client = Elasticsearch(
        cloud_id=os.environ.get('ES_CLOUD_ID'),
        basic_auth=(os.environ.get('ES_USER'), os.environ.get('ES_PASSWORD'))
        )
      else:
        self.client = Elasticsearch(
        os.environ.get('ES_URL'),
        basic_auth=(os.environ.get('ES_USER'), os.environ.get('ES_PASSWORD'))
        )
    except Exception as e:
      logger.error(f"Running into error while initializing ES instances: {e}")
      self.client = None

  def index_faqs(self):
    site_ids = get_merchant_site_ids()

    for id in site_ids:
      site_ids[id] = site_ids[id] + '-faqs'

    self.remove_indices(site_ids)
    self.create_faq_indices(site_ids)

    faqs = get_all_faqs()

    for merchant in faqs:
      for question in faqs[merchant]:
        embedding = encode_sentence(question, PROJECT_ID, ENDPOINT_ID)

        es_data = {
          "question": question,
          "answer": faqs[merchant][question],
          "question_vector": embedding
        }

        self.client.index(index=merchant + '-faqs', document=es_data) 

    return 'indexed faqs'


  def create_faq_indices(self, indices: dict):
    es_index_body = {
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
            "dims": self.dimensions
          }
        }
      }
    }

    for idx in indices:
      self.client.indices.create(index=indices[idx], body=es_index_body)

  def index_products(self):
    site_ids = get_merchant_site_ids()

    for id in site_ids:
      site_ids[id] = site_ids[id] + '-products'

    self.remove_indices(site_ids)
    self.create_product_indices(site_ids)

    variants = get_all_variants()

    for id in variants:
      if variants[id]['merchant_id'] not in site_ids:
        continue

      embedding = encode_sentence(variants[id]['name'], PROJECT_ID, ENDPOINT_ID)
      idx = site_ids[variants[id]['merchant_id']]

      es_data = {
            "id": str(id),
            "name": variants[id]['name'],
            "name_vector": embedding
          }
      
      self.client.index(index=idx, document=es_data) 

    return 'indexed products'
  
  def create_product_indices(self, indices: dict):
    es_index_body = {
      "mappings": {
        "properties": {
          "id": {
            "type": "text"
          },
          "name": {
            "type": "text"
          },
          "name_vector": {
            "type": "dense_vector",
            "dims": self.dimensions
          }
        }
      }
    }

    for idx in indices:
      self.client.indices.create(index=indices[idx], body=es_index_body)
  
  def remove_indices(self, indices: dict):
    for idx in indices:
      self.client.indices.delete(index=indices[idx], ignore=[404])

  def faq_search(self, merchant_site_id: str, query: str):
    embedding = encode_sentence(query, PROJECT_ID, ENDPOINT_ID)

    sem_search = self.client.search(index=merchant_site_id + '-faqs', body={
      "query": {
        "script_score": {
          "query": {
            "match_all": {}
          },
          "script": {
            "source": "cosineSimilarity(params.queryVector, 'question_vector') + 1.0",
            "params": {
              "queryVector": embedding
            }
          }
        }
      }
    })
    
    answers = []

    for hit in sem_search['hits']['hits']:
      answers.append(hit['_source']['answer'])

    if len(answers) == 0:
      answers.append("Very sorry - this is a product FAQ. It doesn't know everything about everything!")

    return answers


  def product_search(self, merchant_site_id: str, query: str):
    embedding = encode_sentence(query, PROJECT_ID, ENDPOINT_ID)

    sem_search = self.client.search(index=merchant_site_id + '-products', body={
      "query": {
        "script_score": {
          "query": {
            "match_all": {}
          },
          "script": {
            "source": "cosineSimilarity(params.queryVector, 'name_vector') + 1.0",
            "params": {
              "queryVector": embedding
            }
          }
        }
      }
    })
    
    product_ids = []

    for hit in sem_search['hits']['hits']:
      product_ids.append(hit['_source']['id'])

    return product_ids

  def suggest_spelling(self, term, idx):
    try:
      sem_sugg = self.client.search(index=idx, body={
            "suggest": {
             "mytermsuggester" : {
                "text": term,
                "term": {
                   "field": "name"
                 }
              }
            }
          })
    except Exception as e:
      logger.error('error suggesting spelling')
      return None
    return sem_sugg
  
  def index_demo(self):
    # pass everything to the demo helper function to avoid clutter in this file
    index_demo_helper(self.client, self.dimensions)
    return 'finished index'

  def faq_demo(self, question):
    # pass everything to the demo helper function to avoid clutter in this file
    return faq_demo(self.client, question)
  
semanticSearch = SemanticSearch()
demo_search = SemanticSearch(dimensions=768, is_demo=True)