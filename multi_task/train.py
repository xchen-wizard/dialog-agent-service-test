from __future__ import annotations

import argparse

import torch
from multi_vendor_data_loader import MultiVendorDataLoader
from torch.optim import AdamW
from tqdm.auto import tqdm
from transformers import get_scheduler
from transformers import T5ForConditionalGeneration
from transformers import T5Tokenizer

argParser = argparse.ArgumentParser()
argParser.add_argument(
    '-d', '--data_dir', help='data directory with training data', required=True)
argParser.add_argument('-m', '--model_dir',
                       help='directory to store output model', required=True)
argParser.add_argument('-b', '--batch_size',
                       help='Batch Size for training', type=int, default=64)
argParser.add_argument(
    '-i', '--iterations', help='Number of iterations to train for', type=int, default=100)
argParser.add_argument('-v', '--vendors', nargs='+',
                       help='vendors on which to train', required=True)
argParser.add_argument('-l', '--learning_rate',
                       help='learning rate', type=float, default=3e-4)
args = argParser.parse_args()

tokenizer = T5Tokenizer.from_pretrained(
    'google/flan-t5-xl', truncation_direction='left')
model = T5ForConditionalGeneration.from_pretrained('google/flan-t5-xl')
data_loader = MultiVendorDataLoader(args.data_dir, tokenizer, args.vendors)

optimizer = AdamW(model.parameters(), lr=args.learning_rate)
num_training_steps = args.iterations
lr_scheduler = get_scheduler(
    name='linear', optimizer=optimizer, num_warmup_steps=0, num_training_steps=num_training_steps,
)

#device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
device = torch.device('mps')
model.to(device)

# progress_bar = tqdm(range(num_training_steps))
# model.train()
# print("---Starting unsupervised pre-training---")
# for _ in range(num_training_steps):
#     input_ids, labels = data_loader.gen_batch(args.batch_size, task_pct=0, response_pct=0, fact_pct=1.0, dst_pct=0)
#     print(f"---Generated batch of size {input_ids.size()}---")
#     loss = model(input_ids=input_ids, labels=labels).loss
#     print("--Loss Computed---")
#     loss.backward()
#     print("--Back Propagation done---")
#     optimizer.step()
#     lr_scheduler.step()
#     print("---Gradient step finished---")
#     optimizer.zero_grad()
#     progress_bar.update(1)

progress_bar = tqdm(range(num_training_steps))
model.train()
print('---Starting training---')
for _ in range(num_training_steps):
    input_ids, labels = data_loader.gen_batch(
        args.batch_size, task_pct=0, response_pct=1.0, fact_pct=0, dst_pct=0)
    print(f'---Generated batch of size {input_ids.size()}, {labels.size()}---')
    loss = model(input_ids=input_ids, labels=labels).loss
    print('--Loss Computed---')
    loss.backward()
    print('--Back Propagation done---')
    optimizer.step()
    lr_scheduler.step()
    print('---Gradient step finished---')
    optimizer.zero_grad()
    progress_bar.update(1)

model.save_pretrained(args.model_dir, state_dict=model.state_dict())
