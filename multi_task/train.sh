#!/usr/bin/env bash
set -e
BASEDIR=$(dirname "$0")
ROOTDIR="${BASEDIR}/.."
cd $ROOTDIR
PYTHONPATH=$PWD python3 multi_task/train_seq2seq.py --finetune_task --data_dir test_data --model_dir model_dir --epochs 5 --batch_size 4 --vendors "Under Luna" AAVRANI "MYOS Pet"
PYTHONPATH=$PWD python3 multi_task/train_seq2seq.py --create_dialogue_data --model_dir model_dir --data_dir test_data --pickle_file dst_data.pkl --vendors "Under Luna" AAVRANI "MYOS Pet"
PYTHONPATH=$PWD python3 multi_task/train_seq2seq.py --finetune_dialogues --pickle_file dst_data.pkl --model_dir model_dir --epochs 5 --batch_size 4 --vendors "Under Luna" AAVRANI "MYOS Pet"
