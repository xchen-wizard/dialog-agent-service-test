import glob
import logging
from multi_task.datasets.dst_dataset import DSTDataset
import traceback
from multi_task.constants import RESPONSE_TASKS

max_conversation_chars_task = 600
max_conversation_chars_cart = 1500


class T5InferenceService:
    def __init__(self, data_dir, model_name=None, model_dir=None):
        """
        obj = T5InferenceService("google/flan-t5-xl", "model_dir", "test_data", ["Under Luna", "AAVRANI", "MYOS Pet"])
        :param model_name: pre-trained model name
        :param model_dir: model directory with finetuned model
        :param data_dir: directory with product sheet and example dialogues
        """
        if model_name is not None and model_dir is not None:
            from transformers import T5Tokenizer, T5ForConditionalGeneration
            self.tokenizer = T5Tokenizer.from_pretrained(model_name)
            self.model = T5ForConditionalGeneration.from_pretrained(model_dir)
        with open(f"{data_dir}/task_descriptions.txt") as f:
            self.task_descriptions = f.read()
        self.response_prediction_prompt = dict()
        fact_sheets = glob.glob(f"{data_dir}/*/fact_sheet.txt")
        for fact_sheet in fact_sheets:
            vendor = fact_sheet.split("/")[1]
            with open(fact_sheet) as f:
                facts = f.read()
            self.response_prediction_prompt[vendor] = f"{vendor} response: {facts}\n"

    def predict(self, text):
        input = self.tokenizer(text, padding=True, return_tensors="pt")
        outputs = self.model.generate(**input, max_new_tokens=128)
        return self.tokenizer.batch_decode(outputs, skip_special_tokens=True)

    def infer(self, conversation, vendor, predict_fn):
        """
        :param conversation: Conversation formatted as follows:
        Seller: Are you interested in..
        Buyer: Yes
        Seller: Ok..
        Buyer: I had a question
        Note that it should always end with Buyer
        :return: dict with different outputs of interest
        """
        # first predict task
        input, _ = create_input_target_task(conversation, "", task_descriptions=self.task_descriptions)
        task = predict_fn(input)[0]

        if any(x in task for x in RESPONSE_TASKS) and vendor in self.response_prediction_prompt:
            conversation += "Seller: "
            response = predict_fn(self.response_prediction_prompt[vendor] + conversation)[0]
            return {"task": task, "response": response}
        if task == 'FinalizeOrder':
            return {'task': task}
        if task == 'CreateOrUpdateOrderCart':
            product_input, _ = create_input_target_cart(conversation, "")
            products = predict_fn(product_input)[0]
            if products == "None":
                return {"task": task, "cart": []}
            else:
                qty_input, _ = create_input_target_cart(conversation, products+";", qty_infer=True)
                qty_list = predict_fn(qty_input)
            try:
                return {"task": task, "cart": list(zip(products.split(","), map(int, qty_list)))}
            except:
                logging.exception(traceback.format_exc())
                return {"task": task}
        return {'task': task}


def create_input_target_task(cls, conversation, target_str, **kwargs):
    return [f"""
predict task based on task descriptions below:
{kwargs['task_descriptions']}
The below is an interaction between buyer and seller:
{conversation[-max_conversation_chars_task:]}
Write a comma separated list of tasks that the buyer wants us to do right now.
"""], [target_str]


def create_input_target_cart(cls, conversation, target_str, **kwargs):
    inputs = [f"""
answer products of interest: 
{conversation[-max_conversation_chars_cart:]}
Write a comma separated list of products that the buyer is interested in purchasing.
"""] if not kwargs.get('qty_infer', False) else []
    products_qty = target_str.split(";")
    products = products_qty[0].strip()
    targets = [products]
    if len(products_qty) > 1:
        targets.extend([s.strip() for s in products_qty[1].strip().split(",")])
        products = products.split(",")
        for product in products:
            inputs.append(
                f"""
answer product quantity:
{conversation[-max_conversation_chars_cart:]}
How many {product} does the buyer want?
                """
            )
    return inputs, targets

