from typing import Dict, Optional

import torch
from miditok.midi_tokenizer import MIDITokenizer
from torch import Tensor, device
from tqdm import tqdm

from scripts.base import BaseModel
from scripts.trainer import Trainer


class ProgramGenerator:
    def __init__(self, model: BaseModel, tokenizer: MIDITokenizer, device: device, sample=True) -> None:
        self.model = model
        self.tokenizer = tokenizer
        self.sample = sample
        self.device = device
    
    def generate(self, n_tokens: int):
        ...
    
    def continue_seq(self, n_tokens: int, seq: Tensor, full_composition: bool=False):
        if seq[-1].item() == self.tokenizer['EOS_None']:
            seq = seq[:-1]

        # Bar_None idx=4
        # Position_0 idx=173
        # Program_0 idx=220 (piano)
        new_instr = torch.tensor([4, 173, 220])
        seq = torch.concatenate([seq, new_instr], dim=-1)

        is_training = self.model.training
        self.model = self.model.to(self.device)
        self.model.eval()
        with torch.no_grad():
            generated_seq = self.generator(n_tokens, seq)
        if is_training:
            self.model.train()

        if full_composition:
            generated_seq = torch.concatenate([seq, generated_seq], dim=-1)
        return generated_seq
    
    def generator(self, n_tokens: int, prompt_seq: Optional[Tensor]=None):
        input_length = self.model.module.input_length
        if prompt_seq is None:
            tokens = torch.zeros(n_tokens, dtype=torch.long)
            tokens[0] = self.tokenizer['']
            token_idx = 1
        else:
            prompt_seq = prompt_seq[:input_length]
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