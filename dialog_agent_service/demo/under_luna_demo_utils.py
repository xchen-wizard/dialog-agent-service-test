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
    while msize > 3300:
        messages.pop(1)
        msize = num_tokens_from_messages(messages)

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

  # sem_search = faq_demo_search(es_client, q1)

  # augmented_prompt = re.sub(r'<FILLERQ>',sem_search[0],prompt)
  # augmented_prompt = re.sub(r'<FILLERA>',sem_search[1],augmented_prompt)

  answer = fill_msg_and_send(question)

  # print("{}\t{}".format(question,answer))
  # focus = get_focus(question+answer)

  return answer

product_data = [
    {
        "Id": "UL001",
        "Brand": "Under Luna",
        "Category": "Hair Care",
        "Product Title": "Unscented Shampoo",
        "Product Description": "With an abundance of scalp-loving, hair softening and hydrating herbs, this nourishing shampoo is essential oil-free, vegan and perfect for anyone from nursing moms to babies to folks wanting clean and clear products.",
        "Small Size Amount": "8 oz",
        "Small Size Price": "$36.00",
        "Large Size Amount": "16 oz",
        "Large Size Price": "$58",
        "Good For": "people with sensitivities, babies and children",
        "Aromas": "essential oil free",
        "Attributes": "Vegan Organic Ingredients Essential Oil Free Pregnancy & Nursing Safe Kid Friendly",
        "Ingredients": "Nettle Leaf Oil: rich in minerals that protect our scalp and strengthen our hair. Plantain Leaf Oil: antiseptic and antibacterial. Organic Golden Jojoba Oil: moisturizing, soothing to the scalp, hydrates hair from within the hair shaft."
    },
    {
        "Id": "UL002",
        "Brand": "Under Luna",
        "Category": "Hair Care",
        "Product Title": "Sweet Baby Orange Shampoo",
        "Product Description": "A gentle, safe, and tear-free shampoo for the whole family, from babies (recommended 6 months and up), to grandparents! The vibrant scent of lavender and sweet orange will boost your mood and re-energize your senses.",
        "Small Size Amount": "8 oz",
        "Small Size Price": "$36.00",
        "Large Size Amount": "16 oz",
        "Large Size Price": "$58",
        "Good For": "the whole family",
        "Aromas": "sweet orange + lavender",
        "Attributes": "Vegan Organic Ingredients Paraben Free Pregnancy & Nursing Safe Kid Friendly",
        "Ingredients": "Organic Chamomile Flower Extract: cleansing, moisturizing, calming, heals minor wounds & soothes irritated scalp or dandruff. \u2022 Organic Lemon Balm Flowers: known as the \"calming\" herb. cleanses hair, increases shine and body, soothes and prevents dandruff. \u2022 Aloe Vera: a staple in Native American culture to remedy skin + scalp wounds and hydration."
    },
    {
        "Id": "UL003",
        "Brand": "Under Luna",
        "Category": "Hair Care",
        "Product Title": "Warrior Shampoo",
        "Product Description": "Just like plants need healthy soil, strong, healthy hair needs a happy scalp. Warrior Shampoo is like a rich fertilizer that restores and revitalizes your scalp and adds elasticity to your hair.",
        "Small Size Amount": "8 oz",
        "Small Size Price": "$36.00",
        "Large Size Amount": "16 oz",
        "Large Size Price": "$58",
        "Good For": "scalp restore + revitalize hair",
        "Aromas": "sage + citrus",
        "Attributes": "Vegan Chemical Free Paraben Free Sulfate Free Cruelty Free",
        "Ingredients": "Organic Horsetail: strengthens hair and supports growth. \u2022 Organic Yarrow Flowers: helps with dandruff, itchiness, and irritation, and balances oil production. \u2022 Organic White Willow Bark: helps exfoliate the scalp, a hair stimulant, great for oily or dandruff-prone hair."
    },
    {
        "Id": "UL004",
        "Brand": "Under Luna",
        "Category": "Hair Care",
        "Product Title": "Unscented Conditioner",
        "Product Description": "Meet our most versatile conditioner! Safe for all ages, with a balanced density, it\u2019s hydrating and great for hair growth, dry ends and tangled ends - ready to please all hair types!",
        "Small Size Amount": "8 oz",
        "Small Size Price": "$34.00",
        "Large Size Amount": "16 oz",
        "Large Size Price": "$56",
        "Good For": "all ages - essential oil-free, kid-friendly",
        "Aromas": "essential oil free",
        "Attributes": "Vegan Organic Ingredients Essential Oil Free Pregnancy & Nursing Safe Kid Friendly",
        "Ingredients": "Rosemary and Bay Hydrosol: A dynamic duo that\u2019s analgesic & anti-inflammatory, from Wildcare. \u2022 Plantain Leaf Oil: natural remedy for healing an irritated scalp such as dandruff or cradle cap. It\u2019s antiseptic and antibacterial. \u2022 Nettle Leaf Oil: rich in minerals, it's a vitamin boost for our scalp and hair."
    },
    {
        "Id": "UL005",
        "Brand": "Under Luna",
        "Category": "Hair Care",
        "Product Title": "Luna Love Conditioner",
        "Product Description": "We put all the love into creating a conditioner to hydrate, soothe, seal up those splitting ends and protect those tresses.",
        "Small Size Amount": "8 oz",
        "Small Size Price": "$34.00",
        "Large Size Amount": "16 oz",
        "Large Size Price": "$56",
        "Good For": "fine - medium, normal - oily hair, kid-friendly",
        "Aromas": "cypress + lavender",
        "Attributes": "Vegan Organic Ingredients Cruelty Free Pregnancy & Nursing Safe Kid Friendly",
        "Ingredients": "Organic Unrefined Avocado Oil: moisturizing, provides strength to the hair fiber which helps with hair growth. \u2022 Organic Golden Jojoba Oil: moisturizing, soothing to the scalp, hydrates hair from within the hair shaft. \u2022 Organic Chamomile Extract: help promote hair strength, prevent split ends, provides hydration and known to restore shine."
    },
    {
        "Id": "UL006",
        "Brand": "Under Luna",
        "Category": "Hair Care",
        "Product Title": "Serenity Conditioner",
        "Product Description": "This one\u2019s for soothing, nourishing, and healing your hair. Kind of like hair-yoga. It\u2019s made with nutrient-rich flowers, moisturizing honey, and luxurious oils like siam wood and bergamot that are all about balance and finding serenity. (Calendula is the skin whisperer of the flowers).",
        "Small Size Amount": "8 oz",
        "Small Size Price": "$34.00",
        "Large Size Amount": "16 oz",
        "Large Size Price": "$56",
        "Good For": "fine - medium, dry/damaged hair",
        "Aromas": "siam wood + geranium + bergamot",
        "Attributes": "Organic Ingredients Chemical Free Paraben Free Cruelty Free Pregnancy & Nursing Safe",
        "Ingredients": "Honey: natural humectant, honey attracts moisture. Full of antioxidants and nutrients. Feeds hair follicles, encouraging hair growth. \u2022 Geranium Hydrosol: rose-like aroma, healing to skin and strengthening to hair. \u2022 Organic Calendula Flower Extract: heals cuts and wounds with its antibacterial and anti-inflammatory properties."
    },
    {
        "Id": "UL007",
        "Brand": "Under Luna",
        "Category": "Hair Care",
        "Product Title": "Revive Conditioner",
        "Product Description": "Our Green Juice for your hair, but better smelling! (Think jasmine). Created with herbal extracts that stimulate growth, strengthen, de-stress and de-frizz your locks. It's pH-balanced and ready to protect the hair from environmental toxins.",
        "Small Size Amount": "8 oz",
        "Small Size Price": "$34.00",
        "Large Size Amount": "16 oz",
        "Large Size Price": "$56",
        "Good For": "medium to thick hair, strengthens hair + stimulates growth",
        "Aromas": "jasmine",
        "Attributes": "Organic Ingredients No Additives Paraben Free Sulfate Free Cruelty Free",
        "Ingredients": "rganic Horsetail: strengthens hair and support growth. \u2022 Organic Yarrow Flowers: helps with dandruff, itchiness, irritation and balances oil production. \u2022 Organic Chamomile Flowers: cleansing, moisturizing, calming, heals minor wounds & soothes irritated scalp or dandruff."
    },
    {
        "Id": "UL008",
        "Brand": "Under Luna",
        "Category": "Hair Care",
        "Product Title": "Ancient Remedy Hair + Scalp Oil",
        "Product Description": "The secret to lustrous, radiant hair? This silky serum right here. It\u2019s packed with the most healing, hydrating, revitalizing and strengthening herbs. And it smells like a night in a gorgeous forest. Use it as a scalp treatment, to heal dandruff or dry scalp, balance oils, encourage growth and strengthen hair. And it tames the frizzies!",
        "Small Size Amount": "UNKNOWN",
        "Small Size Price": "$21.00",
        "Large Size Amount": "UNKNOWN",
        "Large Size Price": "UNKNOWN",
        "Good For": "UNKNOWN",
        "Aromas": "juniper berry + siam wood",
        "Attributes": "Vegan Organic Ingredients No Additives Cruelty Free Pregnancy & Nursing Safe",
        "Ingredients": "Saw Palmetto Berries: used to heal hair loss and a scaly scalp or dandruff. a key ingredient for strong and beautiful hair. \u2022 Organic Yarrow Flowers: antimicrobial + anti-inflammatory. \u2022 Organic Golden Jojoba Oil: used to moisturize and grow hair."
    },
    {
        "Id": "UL009",
        "Brand": "Under Luna",
        "Category": "Hair Care",
        "Product Title": "Tulsi Bloom Shampoo + Conditioner Set",
        "Product Description": "A spirited collaboration between Carly of Under Luna & Cortney of Wildcare with an intention to encourage & reclaim the strength within. Deep green herbs grown in the Wildcare garden & foraged in the untamed Pacific Northwest landscape marry with Under Luna's time-honored haircare formulas. Unlocked is a mineral-rich shampoo & conditioner that nourishes, comforts & re-instills vital nutrients to the hair and scalp. With regular use, you may notice more rapid growth, shiner locks and strengthened hair.",
        "Small Size Amount": "UNKNOWN",
        "Small Size Price": "UNKNOWN",
        "Large Size Amount": "UNKNOWN",
        "Large Size Price": "UNKNOWN",
        "Good For": "all hair\u2014 but especially postpartum and/or brittle hair",
        "Aromas": "tulsi, cypress + sweet orange",
        "Attributes": "UNKNOWN",
        "Ingredients": "Tulsi Leaf + Flowers: Grown and handpicked by Wildcare in Portland, OR. Its antibacterial and antifungal properties have been shown to reduce dandruff, offering relief for a dry, itchy scalp.  \u00b7 Nettle Leaf: Grown and handpicked by Wildcare in Portland, OR. This common weed is powerfully mineral-rich. Its stinging leaves are commonly used in various healing modalities such as arthritis and/or pain relief and dried as a tea to boost iron levels. Rich in chlorophyll, antioxidants + minerals, it's often looked to as an ancient remedy for hair loss. It assists in reducing inflammation on the scalp, (yes even scalps get inflamed due to pollutants and hair product buildup) which in turn keeps the hair follicles clear, paving the way for new growth.  \u00b7 Rosemary + Bay Hydrosol: Grown and distilled by Wildcare. Perhaps one of the best for scalp/hair care. Rosemary contains ursolic acid, which brings oxygen and nutrients to the hair follicles - inspiring new growth. It can also add softness, add shine and ease an itchy scalp. Bay has been shown to stimulate collagen, providing elasticity of each hair = less breakage and more growth. It is equally anti-bacterial and microbial, like Rosemary, helping to prevent dandruff and an irritated scalp.  \u00b7 Horsetail : Foraged and picked in the Pacific Northwest. It is a wet-land loving plant that reproduces by spores instead of seeds! It is said to have the highest silica content in the plant kingdom, and contains a large amount of selenium and cysteine, known for rapidly stimulating hair growth and repairing & protecting strands from the inside out. By improving circulation, horsetail keeps hair follicles clear, contributing to healthy, strengthened hair. The horsetail was mindfully foraged in the Pacific Northwest."
    },
    {
        "Id": "UL010",
        "Brand": "Under Luna",
        "Category": "Body",
        "Product Title": "All Things Oil",
        "Product Description": "our newest addition! Created to be your go-to oil for just about everything, from make-up remover to lotion substitute to eyebrow serum (yes, that\u2019s a thing). Made with rich, non-clogging skin-loving oils that you typically find in high end face serums - because our bodies deserve the best!",
        "Small Size Amount": "2 oz",
        "Small Size Price": "24",
        "Large Size Amount": "8 oz",
        "Large Size Price": "$35",
        "Good For": "UNKNOWN",
        "Aromas": "frankincense and copaiba balsam resins + citrus extracts",
        "Attributes": "UNKNOWN",
        "Ingredients": "Rosehip Seed Oil: full of antioxidants, vitamins A, C, and E, phenolic compounds. Keeps skin hydrated, helps combat acne, protects against sun damage and reduces inflammation. \u2022 Raspberry Seed Oil: can help combat sun damage, boosts elasticity in skin, can help fight acne or irritated skin like eczema. \u2022 Strawberry Seed Oil: great for dry or sensitive skin or acne prone skin. helps improve elasticity, fine lines and brings hydration. \u2022 Meadowfoam Seed Oil: can help create a barrier to prevent moisture from escaping. non-clogging and great for acne prone skin."
    }
]

messages = [
    {"role": "system",
     "content": "You are a kind and helpful catalog product expert. Answer with specific product names and attributes from the catalog where possible. If a 'network error' happens, please revert and resume your answer. Use only the following catalog dataset to supply all answers:" + str(
         product_data)}
]