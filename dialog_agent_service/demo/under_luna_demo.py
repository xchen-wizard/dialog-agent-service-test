import os
import sys
import time
import re
import json
import openai
import tiktoken
from termcolor import colored
from nltk.tokenize import sent_tokenize
import configparser
from elasticsearch import Elasticsearch, helpers
from sentence_transformers import SentenceTransformer, util

class ProdCierge():
    """
    """
    def search_one(self, indexname, question):
        question_embedding = self.model.encode(question)
        sem_search = None
        sem_search = self.es.search(index=indexname, body={
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
                    # top_product = hit['_source']['product_title'].strip('\n')
                    top_question = hit['_source']['text'].strip('\n')
                    top_answer = hit['_source']['answer'].strip('\n')
                    top_source = hit['_source']['source'].strip('\n')
                    top_score = sem_search['hits']['hits'][0]['_score']
                    break
                sem_search = (top_question, top_answer, top_source, top_score, indexname)
            else:
                sem_search = None
        else:
            sem_search = None
        return sem_search
    
    def __init__(self, configuration_file_name, index_names):
        self.input_file_dicts_list = []
        self.index_names = []
        self.chunk_size = 500
        self.product_indices_prefix = ""
        self.index_names = index_names
        
        print("Loading elasticsearch index...")
        self.config = configparser.ConfigParser()
        self.config.read(configuration_file_name)
        
        # Instantiate a client instance
        self.client = Elasticsearch(
          cloud_id=os.environ.get('ES_CLOUD_ID'),
          basic_auth=(os.environ.get('ES_USER'), os.environ.get('ES_PASSWORD'))
        )
        print(self.client)
        
        self.dimensions = 768
        self.model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
    
    """
    """
    
    def print_fields_and_types(self, index_name):
        idx_list = self.client.cat.indices(h='index', s='index').split()
        for _ in idx_list:
            print(_)
        if index_name not in idx_list:
            print("Index {} not found".format(index_name))
            sys.exit()
        
        mappings = self.client.indices.get_mapping(index=index_name)
        properties = mappings[index_name]["mappings"]["properties"]
        
        def print_recursive(properties, parent_path=""):
            for field, field_mapping in properties.items():
                field_path = parent_path + field
                field_type = field_mapping["type"] if "type" in field_mapping else "object"
                print(f"{field_path}: {field_type}")
                
                if "properties" in field_mapping:
                    print_recursive(field_mapping["properties"], field_path + ".")
        print_recursive(properties)

# from openai.api_key import get_secret_key

openai.api_key = "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"

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

    
"""
"""
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
  
"""
product_data = [
    {
        "Product Title": "Unscented Shampoo",
        "Product Description": "With an abundance of scalp-loving, hair softening and hydrating herbs, this nourishing shampoo is essential oil-free, vegan and perfect for anyone from nursing moms to babies to folks wanting clean and clear products.",
        "Size": "8 oz",
        "Price": "$36.00",
        "Good For": "people with sensitivities, babies and children",
        "Aromas": "essential oil free",
        "Attributes": "Vegan Organic Ingredients Essential Oil Free Pregnancy & Nursing Safe Kid Friendly",
        "Ingredients": "Nettle Leaf Oil: rich in minerals that protect our scalp and strengthen our hair. Plantain Leaf Oil: antiseptic and antibacterial. Organic Golden Jojoba Oil: moisturizing, soothing to the scalp, hydrates hair from within the hair shaft."
    },
    {
        "Product Title": "Sweet Baby Orange Shampoo",
        "Product Description": "A gentle, safe, and tear-free shampoo for the whole family, from babies (recommended 6 months and up), to grandparents! The vibrant scent of lavender and sweet orange will boost your mood and re-energize your senses.",
        "Size": "8 oz",
        "Price": "$36.00",
        "Good For": "the whole family",
        "Aromas": "sweet orange + lavender",
        "Attributes": "Vegan Organic Ingredients Paraben Free Pregnancy & Nursing Safe Kid Friendly",
        "Ingredients": "Organic Chamomile Flower Extract: cleansing, moisturizing, calming, heals minor wounds & soothes irritated scalp or dandruff. \u2022 Organic Lemon Balm Flowers: known as the \"calming\" herb. cleanses hair, increases shine and body, soothes and prevents dandruff. \u2022 Aloe Vera: a staple in Native American culture to remedy skin + scalp wounds and hydration."
    },
    {
        "Product Title": "Warrior Shampoo",
        "Product Description": "Just like plants need healthy soil, strong, healthy hair needs a happy scalp. Warrior Shampoo is like a rich fertilizer that restores and revitalizes your scalp and adds elasticity to your hair.",
        "Size": "8 oz",
        "Price": "$36.00",
        "Good For": "scalp restore + revitalize hair",
        "Aromas": "sage + citrus",
        "Attributes": "Vegan Chemical Free Paraben Free Sulfate Free Cruelty Free",
        "Ingredients": "Organic Horsetail: strengthens hair and supports growth. \u2022 Organic Yarrow Flowers: helps with dandruff, itchiness, and irritation, and balances oil production. \u2022 Organic White Willow Bark: helps exfoliate the scalp, a hair stimulant, great for oily or dandruff-prone hair."
    },
    {
        "Product Title": "Unscented Conditioner",
        "Product Description": "Meet our most versatile conditioner! Safe for all ages, with a balanced density, it\u2019s hydrating and great for hair growth, dry ends and tangled ends - ready to please all hair types!",
        "Size": "8 oz",
        "Price": "$34.00",
        "Good For": "all ages - essential oil-free, kid-friendly",
        "Aromas": "essential oil free",
        "Attributes": "Vegan Organic Ingredients Essential Oil Free Pregnancy & Nursing Safe Kid Friendly",
        "Ingredients": "Rosemary and Bay Hydrosol: A dynamic duo that\u2019s analgesic & anti-inflammatory, from Wildcare. \u2022 Plantain Leaf Oil: natural remedy for healing an irritated scalp such as dandruff or cradle cap. It\u2019s antiseptic and antibacterial. \u2022 Nettle Leaf Oil: rich in minerals, it's a vitamin boost for our scalp and hair."
    },
    {
        "Product Title": "Luna Love Conditioner",
        "Product Description": "We put all the love into creating a conditioner to hydrate, soothe, seal up those splitting ends and protect those tresses.",
        "Size": "8 oz",
        "Price": "$34.00",
        "Good For": "fine - medium, normal - oily hair, kid-friendly",
        "Aromas": "cypress + lavender",
        "Attributes": "Vegan Organic Ingredients Cruelty Free Pregnancy & Nursing Safe Kid Friendly",
        "Ingredients": "Organic Unrefined Avocado Oil: moisturizing, provides strength to the hair fiber which helps with hair growth. \u2022 Organic Golden Jojoba Oil: moisturizing, soothing to the scalp, hydrates hair from within the hair shaft. \u2022 Organic Chamomile Extract: help promote hair strength, prevent split ends, provides hydration and known to restore shine."
    },
    {
        "Product Title": "Serenity Conditioner",
        "Product Description": "This one\u2019s for soothing, nourishing, and healing your hair. Kind of like hair-yoga. It\u2019s made with nutrient-rich flowers, moisturizing honey, and luxurious oils like siam wood and bergamot that are all about balance and finding serenity. (Calendula is the skin whisperer of the flowers).",
        "Size": "8 oz",
        "Price": "$34.00",
        "Good For": "fine - medium, dry/damaged hair",
        "Aromas": "siam wood + geranium + bergamot",
        "Attributes": "Organic Ingredients Chemical Free Paraben Free Cruelty Free Pregnancy & Nursing Safe",
        "Ingredients": "Honey: natural humectant, honey attracts moisture. Full of antioxidants and nutrients. Feeds hair follicles, encouraging hair growth. \u2022 Geranium Hydrosol: rose-like aroma, healing to skin and strengthening to hair. \u2022 Organic Calendula Flower Extract: heals cuts and wounds with its antibacterial and anti-inflammatory properties."
    },
    {
        "Product Title": "Revive Conditioner",
        "Product Description": "Our Green Juice for your hair, but better smelling! (Think jasmine). Created with herbal extracts that stimulate growth, strengthen, de-stress and de-frizz your locks. It's pH-balanced and ready to protect the hair from environmental toxins.",
        "Size": "8 oz",
        "Price": "$34.00",
        "Good For": "medium to thick hair, strengthens hair + stimulates growth",
        "Aromas": "jasmine",
        "Attributes": "Organic Ingredients No Additives Paraben Free Sulfate Free Cruelty Free",
        "Ingredients": "Organic Horsetail: strengthens hair and support growth. \u2022 Organic Yarrow Flowers: helps with dandruff, itchiness, irritation and balances oil production. \u2022 Organic Chamomile Flowers: cleansing, moisturizing, calming, heals minor wounds & soothes irritated scalp or dandruff."
    },
]
"""

messages = []

es_instance = ProdCierge('./data/es_config.yml',
                         ['faqz_underluna_faqcat'])
print(es_instance)

prompt1 = "combine this question/answer pair into a single clear consistent statement: <FILLERQ>, <FILLERA>."
qs = [
    'what shampoo helps with dandruff?',
    'what does it cost?',
    "what would be safest for children?",
    "which one has a lavender type of scent?",
    "does warrior shampoo contain parabens?",
    "what size does it come in?",
    "what are its ingredients?",
    "can any product address tangles?",
    "hey are glass bottles really safe?",
    "I have post partum hair loss",
    "why is shipping so expensive?",
    "reset",
    "i need a shampoo that's totally organic",
    "sounds good what does that cost?"
]
focus = None
curr_focus = None
for _ in es_instance.index_names:
    for q1 in qs:
        if q1 == 'reset':
            messages = []
            continue
        original = q1
        if focus != None:
            if ' it ' in q1.lower() and focus != None:
                q1 = q1.replace(' it ',' ' + focus + ' ')
            if ' its ' in q1.lower() and focus != None:
                q1 = q1.replace(' its ', ' ' + focus + ' ')
            elif ' that ' in q1.lower() and focus != None:
                q1 = q1.replace(' that ',' ' + focus + ' ')
        # print("Focus = {}".format(focus))
        sem_search = es_instance.search_one(_, q1)
        prompt1a = re.sub(r'<FILLERQ>',sem_search[0],prompt1)
        prompt1a = re.sub(r'<FILLERA>',sem_search[1],prompt1a)
        answer = fill_msg_and_send(prompt1a)
        print("{}\t{}".format(original,answer))
        focus = get_focus(q1+answer)
        print("==================================")
sys.exit()