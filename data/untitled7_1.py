#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
"""Untitled7_3.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1KcqpbUr2qlQm0OZ3TKRMmd5AxPkyskaO
"""

#from google.colab import drive
#drive.mount('/content/drive')

# Commented out IPython magic to ensure Python compatibility.
# %cd "/content/drive/MyDrive/archive"

# Create a directory named model to save your model

output_models_dir = "../model3"

#%%capture
#!pip3 install datasets==1.4.1
#!pip3 install transformers==4.4.0
#!pip3 install torchaudio
#!pip3 install jiwer
#!pip3 install pandas
#!pip install torchaudio==0.7
#!pip install pandas==1.1.5

# Commented out IPython magic to ensure Python compatibility.
#cd "archive/data"

import pandas as pd

data = pd.read_csv('Train_2000.csv')
data['ID'] = 'clips/' + data['ID'] + '.mp3'
data.to_csv('train.csv',index=False)
data.head()

# Create training folds(5 folds)

from datasets import load_dataset, load_metric,concatenate_datasets



vals_ds = load_dataset('csv',data_files=['train.csv'], split=[f'train[{k}%:{k+20}%]' for k in range(0, 100, 20)])


voice_val = vals_ds[0].remove_columns(['up_votes', 'down_votes', 'age', 'gender'])
#voice_val = vals_ds[0]

trains_ds = load_dataset('csv',data_files=['train.csv'], split=[f'train[:{k}%]+train[{k+20}%:]' for k in range(0, 100, 20)])

voice_train = trains_ds[0].remove_columns(['up_votes', 'down_votes', 'age', 'gender'])
#voice_train = trains_ds[0]

from datasets import ClassLabel
import random
import pandas as pd
from IPython.display import display, HTML

def show_random_elements(dataset, num_examples=10):
    assert num_examples <= len(dataset), "Can't pick more elements than there are in the dataset."
    picks = []
    for _ in range(num_examples):
        pick = random.randint(0, len(dataset)-1)
        while pick in picks:
            pick = random.randint(0, len(dataset)-1)
        picks.append(pick)
    
    df = pd.DataFrame(dataset[picks])
    display(HTML(df.to_html()))

# Display the dataset

show_random_elements(voice_train, num_examples=20)

import re
chars_to_ignore_regex = '[\,\؟\.\!\-\;\:\"\)\(\«\»\؛\—\ـ\_\،\“\%\‘\”]'

def remove_special_characters(batch):  
    batch["transcription"] = re.sub(chars_to_ignore_regex,' ',batch["transcription"]).lower()+" "
    return batch


voice_train = voice_train.map(remove_special_characters)
voice_val = voice_val.map(remove_special_characters)

# Display cleaned data

show_random_elements(voice_train, num_examples=20)

def extract_all_chars(batch):
  all_text = " ".join(batch["transcription"])
  vocab = list(set(all_text))
  return {"vocab": [vocab], "all_text": [all_text]}

vocab_train = voice_train.map(extract_all_chars, batched=True, batch_size=-1, keep_in_memory=True, remove_columns=voice_train.column_names)
vocab_val = voice_val.map(extract_all_chars, batched=True, batch_size=-1, keep_in_memory=True, remove_columns=voice_val.column_names)

vocab_list = list(set(vocab_train["vocab"][0]) | set(vocab_val["vocab"][0]))

vocab_dict = {v: k for k, v in enumerate(vocab_list)}
vocab_dict

vocab_dict["|"] = vocab_dict[" "]
del vocab_dict[" "]

vocab_dict["[UNK]"] = len(vocab_dict)
vocab_dict["[PAD]"] = len(vocab_dict)
len(vocab_dict)

# Prepare vocabulary
import json
with open(f"{output_models_dir}/vocab.json", 'w') as vocab_file:
    json.dump(vocab_dict, vocab_file)

# Tokenization
from transformers import Wav2Vec2CTCTokenizer

tokenizer = Wav2Vec2CTCTokenizer(f"{output_models_dir}/vocab.json", unk_token="[UNK]", pad_token="[PAD]", word_delimiter_token="|")

from transformers import Wav2Vec2FeatureExtractor

feature_extractor = Wav2Vec2FeatureExtractor(feature_size=1, sampling_rate=16000, padding_value=0.0, do_normalize=True, return_attention_mask=True)

from transformers import Wav2Vec2Processor

processor = Wav2Vec2Processor(feature_extractor=feature_extractor, tokenizer=tokenizer)

processor.save_pretrained(output_models_dir)



voice_train[0]

import torchaudio
import torch

# Apply transformation to 0.5 of the training data(reduce speed + reverbration)

def speech_file_to_array_fn(batch):
    speech_array, sampling_rate = torchaudio.load(batch["ID"])
    resampler = torchaudio.transforms.Resample(sampling_rate, 16_000)
    batch["speech"] = resampler(speech_array).squeeze().numpy()
    batch["sampling_rate"] = 16000
    batch["target_text"] = batch["transcription"]
    return batch

    #speech_array, sampling_rate = torchaudio.load(batch["path"])
    #batch["speech"] = speech_array[0].numpy()
    #batch["sampling_rate"] = sampling_rate
    #batch["target_text"] = batch["sentence"]
    #return batch
def speech_file_to_array_fn_aug(batch):
    speech_array, sampling_rate = torchaudio.load(batch["ID"])
    resampler = torchaudio.transforms.Resample(sampling_rate, 16_000)
    #batch["speech"] = resampler(speech_array).squeeze().numpy()
    effects = [
           ["lowpass", "-1", "300"], # apply single-pole lowpass filter
           ["speed", "0.9"],  # reduce the speed
                     # This only changes sample rate, so it is necessary to
                     # add `rate` effect with original sample rate after this.
           ["rate", f"{sampling_rate}"],
           #["reverb", "-w"],  # Reverbration gives some dramatic feeling
           ]
    effects2 = [["reverb","-w"]]

    # Apply effects
    prob = torch.rand(1)
    rever = torch.rand(1)
    if prob > 0.5:
      waveform2, sample_rate2 = torchaudio.sox_effects.apply_effects_tensor(speech_array, sampling_rate, effects) 
      batch["speech"] = resampler(waveform2).squeeze().numpy()
      batch["sampling_rate"] = 16000
      batch["target_text"] = batch["transcription"]
    if rever>0.5:
      waveform3, sample_rate3 = torchaudio.sox_effects.apply_effects_tensor(speech_array, sampling_rate, effects2) 
      batch["speech"] = resampler(waveform3).squeeze().numpy()
      batch["sampling_rate"] = 16000
      batch["target_text"] = batch["transcription"]  


    batch["speech"] = resampler(speech_array).squeeze().numpy()
    batch["sampling_rate"] = 16000
    batch["target_text"] = batch["transcription"]
    return batch
#voice_val = voice_val.map(speech_file_to_array_fn, remove_columns=voice_val.column_names,num_proc=1)

voice_train = voice_train.map(speech_file_to_array_fn_aug,remove_columns=voice_train.column_names,num_proc=1) 
voice_val = voice_val.map(speech_file_to_array_fn, remove_columns=voice_val.column_names,num_proc=1)

#tokenizer.save_pretrained("https://huggingface.co/fkHug/model3FromWav2vec")
#processor.save_pretrained("https://huggingface.co/fkHug/model3FromWav2vec")

import IPython.display as ipd
import numpy as np
import random
# Play audio
rand_int = random.randint(0, len(voice_train)-1)

ipd.Audio(data=np.asarray(voice_train[rand_int]["speech"]), autoplay=True, rate=16000)

rand_int = random.randint(0, len(voice_train)-1)

print("Target text:", voice_train[rand_int]["target_text"])
print("Input array shape:", np.asarray(voice_train[rand_int]["speech"]).shape)
print("Sampling rate:", voice_train[rand_int]["sampling_rate"])

def prepare_dataset(batch):
    # check that all files have the correct sampling rate
    assert (
        len(set(batch["sampling_rate"])) == 1
    ), f"Make sure all inputs have the same sampling rate of {processor.feature_extractor.sampling_rate}."

    batch["input_values"] = processor(batch["speech"], sampling_rate=batch["sampling_rate"][0]).input_values
    
    with processor.as_target_processor():
        batch["labels"] = processor(batch["target_text"]).input_ids
    return batch

voice_train = voice_train.map(prepare_dataset, remove_columns=voice_train.column_names, batch_size=8, num_proc=4, batched=True)
voice_val = voice_val.map(prepare_dataset, remove_columns=voice_val.column_names, batch_size=8, num_proc=4, batched=True)

import torch

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

@dataclass
class DataCollatorCTCWithPadding:
    """
    Data collator that will dynamically pad the inputs received.
    Args:
        processor (:class:`~transformers.Wav2Vec2Processor`)
            The processor used for proccessing the data.
        padding (:obj:`bool`, :obj:`str` or :class:`~transformers.tokenization_utils_base.PaddingStrategy`, `optional`, defaults to :obj:`True`):
            Select a strategy to pad the returned sequences (according to the model's padding side and padding index)
            among:
            * :obj:`True` or :obj:`'longest'`: Pad to the longest sequence in the batch (or no padding if only a single
              sequence if provided).
            * :obj:`'max_length'`: Pad to a maximum length specified with the argument :obj:`max_length` or to the
              maximum acceptable input length for the model if that argument is not provided.
            * :obj:`False` or :obj:`'do_not_pad'` (default): No padding (i.e., can output a batch with sequences of
              different lengths).
        max_length (:obj:`int`, `optional`):
            Maximum length of the ``input_values`` of the returned list and optionally padding length (see above).
        max_length_labels (:obj:`int`, `optional`):
            Maximum length of the ``labels`` returned list and optionally padding length (see above).
        pad_to_multiple_of (:obj:`int`, `optional`):
            If set will pad the sequence to a multiple of the provided value.
            This is especially useful to enable the use of Tensor Cores on NVIDIA hardware with compute capability >=
            7.5 (Volta).
    """

    processor: Wav2Vec2Processor
    padding: Union[bool, str] = True
    max_length: Optional[int] = None
    max_length_labels: Optional[int] = None
    pad_to_multiple_of: Optional[int] = None
    pad_to_multiple_of_labels: Optional[int] = None

    def __call__(self, features: List[Dict[str, Union[List[int], torch.Tensor]]]) -> Dict[str, torch.Tensor]:
        # split inputs and labels since they have to be of different lenghts and need
        # different padding methods
        input_features = [{"input_values": feature["input_values"]} for feature in features]
        label_features = [{"input_ids": feature["labels"]} for feature in features]

        batch = self.processor.pad(
            input_features,
            padding=self.padding,
            max_length=self.max_length,
            pad_to_multiple_of=self.pad_to_multiple_of,
            return_tensors="pt",
        )
        with self.processor.as_target_processor():
            labels_batch = self.processor.pad(
                label_features,
                padding=self.padding,
                max_length=self.max_length_labels,
                pad_to_multiple_of=self.pad_to_multiple_of_labels,
                return_tensors="pt",
            )

        # replace padding with -100 to ignore loss correctly
        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)

        batch["labels"] = labels

        return batch

data_collator = DataCollatorCTCWithPadding(processor=processor, padding=True)

wer_metric = load_metric("wer")

def compute_metrics(pred):
    pred_logits = pred.predictions
    pred_ids = np.argmax(pred_logits, axis=-1)

    pred.label_ids[pred.label_ids == -100] = processor.tokenizer.pad_token_id

    pred_str = processor.batch_decode(pred_ids)
    # we do not want to group tokens when computing the metrics
    label_str = processor.batch_decode(pred.label_ids, group_tokens=False)

    wer = wer_metric.compute(predictions=pred_str, references=label_str)

    return {"wer": wer}

from transformers import Wav2Vec2ForCTC

model = Wav2Vec2ForCTC.from_pretrained(
    "facebook/wav2vec2-large-xlsr-53", 
    attention_dropout=0.05,
    hidden_dropout=0.05,
    feat_proj_dropout=0.0,
    mask_time_prob=0.05,
    layerdrop=0.1,
    gradient_checkpointing=True, 
    ctc_loss_reduction="mean",
    pad_token_id=processor.tokenizer.pad_token_id,
    vocab_size=len(processor.tokenizer)
)

model.freeze_feature_extractor()

from transformers import TrainingArguments

training_args = TrainingArguments(
  output_dir=output_models_dir,
  #output_dir="dev/",
  group_by_length=True,
  per_device_train_batch_size=16,
  #per_device_eval_batch_size=32,
  gradient_accumulation_steps=2,
  dataloader_num_workers = 1,
  evaluation_strategy="steps",
  num_train_epochs=51,
  #fp16=True,
  save_steps=500,
  eval_steps=500,
  logging_steps=500,
  learning_rate=1e-4,
  #warmup_steps=1000,
  warmup_steps=500,
  save_total_limit=1
  #save_total_limit=2
)

from transformers import Trainer

trainer = Trainer(
    model=model,
    data_collator=data_collator,
    args=training_args,
    compute_metrics=compute_metrics,
    train_dataset=voice_train,
    eval_dataset=voice_val,
    tokenizer=processor.feature_extractor,
)

trainer.train()

# Commented out IPython magic to ensure Python compatibility.
#cd "./archive/data"

import torch
import torchaudio
from datasets import load_dataset
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

# Inference on test data

test_dataset = load_dataset('csv',data_files=['SampleSubmission_2000.csv'])



processor = Wav2Vec2Processor.from_pretrained(output_models_dir)
model = Wav2Vec2ForCTC.from_pretrained(f"{output_models_dir}/checkpoint-4000")
model.to("cuda")


# Preprocessing the datasets.
# We need to read the aduio files as arrays
def speech_file_to_array_fn(batch):
    speech_array, sampling_rate = torchaudio.load(f"clips/{batch['ID']}.mp3")
    resampler = torchaudio.transforms.Resample(sampling_rate, 16000)
    batch["speech"] = resampler(speech_array).squeeze().numpy()
    return batch
  

test_dataset = test_dataset.map(speech_file_to_array_fn)

def evaluate(batch):
    inputs = processor(batch["speech"], sampling_rate=16000, return_tensors="pt", padding=True)

    with torch.no_grad():
         logits = model(inputs.input_values.to("cuda"), attention_mask=inputs.attention_mask.to("cuda")).logits

    pred_ids = torch.argmax(logits, dim=-1)
    batch["transcription"] = processor.batch_decode(pred_ids)
    return batch

result = test_dataset.map(evaluate, batched=True, batch_size=8)

print("Prediction:", result)

import pandas as pd


sub = pd.read_csv('SampleSubmission_2000.csv')
sub.head()

result

# fill the empty audio with None
final_pred = [ 'None' if pred=='' else pred for pred in result['train']['transcription']]
final_pred[30]

sub['transcription'] =  final_pred
sub.to_csv('submission.csv',index=False)
sub.head(15)

import IPython.display as ipd
import numpy as np

speech_array, sampling_rate = torchaudio.load(f"clips/{sub['ID'][4]}.mp3")
resampler = torchaudio.transforms.Resample(sampling_rate, 16000)
batch = resampler(speech_array).squeeze().numpy()
ipd.Audio(data=np.asarray(batch), autoplay=True, rate=16000)