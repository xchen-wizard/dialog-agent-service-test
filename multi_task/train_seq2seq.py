from __future__ import annotations

import os

from transformers import DataCollatorForSeq2Seq
from transformers import Seq2SeqTrainer
from transformers import Seq2SeqTrainingArguments
from transformers import T5ForConditionalGeneration
from transformers import T5Tokenizer

from multi_task.datasets.dialogue_dataset import DialogueDataset
from multi_task.datasets.dst_dataset import DSTDataset


def train_model(dataset, model_dir=None, model_name=None, use_checkpoint=False, epochs=2, batch_size=2):
    tokenizer = T5Tokenizer.from_pretrained(model_name)
    model = T5ForConditionalGeneration.from_pretrained(
        model_dir if use_checkpoint else model_name)
    # Data collator
    label_pad_token_id = -100
    data_collator = DataCollatorForSeq2Seq(
        tokenizer,
        model=model,
        label_pad_token_id=label_pad_token_id,
        padding=True,
        return_tensors='pt',
    )
    args = Seq2SeqTrainingArguments(
        output_dir=model_dir,
        overwrite_output_dir=True,
        per_device_train_batch_size=batch_size,
        num_train_epochs=epochs,
        optim='adafactor',
        logging_steps=5,
    )
    trainer = Seq2SeqTrainer(
        model=model,
        args=args,
        train_dataset=dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
    )
    trainer.train()
    trainer.save_model()


def predict_task(text):
    with open(f'{predict_task.data_dir}/task_descriptions.txt') as f:
        task_descriptions = f.read()

    input_text = DSTDataset.create_input_task(
        text, task_descriptions=task_descriptions)
    input = predict_task.tokenizer(input_text, return_tensors='pt')
    outputs = predict_task.model.generate(**input, max_new_tokens=128)
    return predict_task.tokenizer.decode(outputs[0], skip_special_tokens=True)


if __name__ == '__main__':
    import pickle
    import argparse
    model_name = 'google/flan-t5-xl'
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data_dir',
                        help='data directory with training data')
    parser.add_argument('-m', '--model_dir',
                        help='directory to store output model')
    parser.add_argument('-b', '--batch_size',
                        help='Batch Size for training', type=int, default=2)
    parser.add_argument(
        '-e', '--epochs', help='Number of epochs to train for', type=int, default=15)
    parser.add_argument('-v', '--vendors', nargs='+',
                        help='vendors on which to train', required=True)
    parser.add_argument('-p', '--pickle_file',
                        help='Output pickle file to store dialogues')
    parser.add_argument('-tt', '--finetune_task',
                        help='Finetune the model on tasks', action='store_true')
    parser.add_argument('-cd', '--create_dialogue_data',
                        help='Create the training data for response finetuning', action='store_true')
    parser.add_argument('-td', '--finetune_dialogues',
                        help='Finetune the model on dialogues', action='store_true')
    args = parser.parse_args()
    assert sum([args.finetune_task, args.create_dialogue_data,
               args.finetune_dialogues]) == 1
    if args.finetune_task:
        train_model(
            DSTDataset(T5Tokenizer.from_pretrained(model_name), [
                       f'{args.data_dir}/{vendor}/dialogues' for vendor in args.vendors], f'{args.data_dir}/task_descriptions.txt'),
            model_name=model_name, model_dir=args.model_dir, use_checkpoint=False, epochs=args.epochs, batch_size=args.batch_size,
        )
    if args.create_dialogue_data:
        predict_task.tokenizer = T5Tokenizer.from_pretrained(model_name)
        predict_task.model = T5ForConditionalGeneration.from_pretrained(
            args.model_dir)
        predict_task.data_dir = args.data_dir
        dst_data = DialogueDataset(
            T5Tokenizer.from_pretrained(model_name), args.vendors, predict_task, {
                'StartOrBuildOrder', 'FinalizeOrder'},
        )
        with open(args.pickle_file, 'wb') as f:
            pickle.dump(dst_data, f)
    if args.finetune_dialogues:
        with open(args.pickle_file, 'rb') as f:
            obj = pickle.load(f)
        train_model(obj, model_name=model_name, model_dir=args.model_dir,
                    use_checkpoint=True, epochs=args.epochs, batch_size=args.batch_size)
