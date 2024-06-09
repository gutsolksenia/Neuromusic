from typing import Dict, Optional

import torch
from miditok.midi_tokenizer import MIDITokenizer
from torch import Tensor, device
from tqdm import tqdm

from scripts.base import BaseModel
from scripts.trainer import Trainer
from scripts.tokenizers import SeqREMI

class ProgramGenerator:
    def __init__(self, model: BaseModel, tokenizer: SeqREMI, device: device, sample=True) -> None:
        self.model = model
        self.tokenizer = tokenizer
        self.sample = sample
        self.device = device
        self.data_parallel = isinstance(model, torch.nn.DataParallel)
    
    def generate(self, n_tokens: int):
        ...
    
    def continue_seq(self, seq: Tensor, full_composition: bool=False):
        if seq[-1].item() == self.tokenizer['EOS_None']:
            seq = seq[:-1]

        # Bar_None idx=4
        # Position_0 idx=173
        # Program_0 idx=220 (piano)
        program = "Program_40"
        new_instr = torch.tensor([
            self.tokenizer.vocab["Bar_None"],
            self.tokenizer.vocab["Position_0"],
            self.tokenizer.vocab[program]])
        seq = torch.concatenate([seq, new_instr], dim=-1)

        is_training = self.model.training
        self.model = self.model.to(self.device)
        self.model.eval()
        with torch.no_grad():
            generated_seq = self.generator(seq, program)
        if is_training:
            self.model.train()

        if full_composition:
            generated_seq = torch.concatenate([seq, generated_seq], dim=-1)
        return generated_seq
    
    def generator(self, prompt_seq: Tensor, program=None):
        program_token_ids = []
        for (k, v) in self.tokenizer.vocab.items():
            if k.startswith("Program_"):
                program_token_ids.append(v)
        program_token_ids_tensor = torch.tensor(program_token_ids).cuda()

        input_length = self.model.module.input_length if self.data_parallel else self.model.input_length
        print(f"actual_input_length={prompt_seq.shape[0]}")
        prompt_seq = prompt_seq[:input_length]
        n_tokens =  prompt_seq.shape[0] #TODO
        tokens = torch.zeros(n_tokens + prompt_seq.shape[0], dtype=torch.long)
        tokens[:] = self.tokenizer['PAD_None']
        tokens[:prompt_seq.shape[0]] = prompt_seq
        token_idx = prompt_seq.shape[0]
        mask = torch.zeros(tokens.shape[0])
        mask[:token_idx] = 1
        
        for i in tqdm(range(n_tokens)):
            start_idx = max(0, token_idx - input_length)
            batch = {
                'input_ids': tokens[start_idx:token_idx].unsqueeze(0),
                'target_ids': tokens[start_idx + 1:token_idx + 1].clone().detach().unsqueeze(0),
                'input_mask': mask[start_idx:token_idx].unsqueeze(0),
                'target_mask': mask[start_idx + 1:token_idx + 1].unsqueeze(0)
            }
            Trainer.move_batch_to_device(batch, self.device)
            new_token = self.pred_next_token(batch)
            if program is not None \
                and torch.any(torch.isin(program_token_ids_tensor, new_token, assume_unique=True)): #Check if new token is program token
                new_token = torch.tensor(self.tokenizer.vocab[program]).cuda()
            tokens[token_idx] = new_token
            mask[token_idx] = 1
            token_idx += 1
            if new_token == self.tokenizer['EOS_None']:
                break

        return tokens[prompt_seq.shape[0]:token_idx]

    def pred_next_token(self, batch: Dict):
        logits = self.model(**batch)['logits'][:, -1, :]
        if self.sample:
            distribution = torch.distributions.categorical.Categorical(
                logits=logits
            )
            next_token = distribution.sample()
        else:
            next_token = torch.argmax(logits).item()
        return next_token