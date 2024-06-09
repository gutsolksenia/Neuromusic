from miditok import REMI, TokenizerConfig, TokSequence, constants
from typing import List
import copy


class SeqREMI(REMI):
    def __init__(self, tokenizer_config: TokenizerConfig, max_bar_embedding=None, *args, **kwargs):
        super().__init__(tokenizer_config, max_bar_embedding=max_bar_embedding, *args, **kwargs)
        delegate_config:TokenizerConfig = copy.deepcopy(tokenizer_config)
        delegate_config.one_token_stream_for_programs = False
        self.delegate = REMI(delegate_config, max_bar_embedding=max_bar_embedding, *args, **kwargs)
        # print(f"self.tokens={self.vocab}")
        # print(f"delegate.tokens={self.delegate.vocab}")
        self.inv_vocab = {v: k for k, v in self.vocab.items()}

    
    def _midi_to_tokens(self, *args, **kwargs) -> TokSequence:
        # print("_midi_to_tokens")
        delegate_tokens: List[TokSequence] = self.delegate._midi_to_tokens(*args, **kwargs)
        # print(f"delegate_tokens_len={len(delegate_tokens)}")
        concat_tokens: List[str] = []
        concat_ids: List[int] = []
        concat_bytes: str = None
        concat_events: List = []
        ids_bpe_encoded = False 
        _ids_no_bpe: List[int] = None

        # print(f"got {len(parent_tokens)} programs")
        for tok_seq in delegate_tokens:
            concat_tokens.extend(tok_seq.tokens)
            # print(f"concat_tokens={tok_seq.tokens[:10]}..")
            concat_ids.extend(tok_seq.ids)
            # print(f"tok_seq len={len(tok_seq)}")
            # print(f"tok_seq={tok_seq}")
            if concat_bytes is None:
                concat_bytes = tok_seq.bytes
            elif tok_seq.bytes is not None:
                concat_bytes += tok_seq.bytes
            concat_events.extend(tok_seq.events)
            ids_bpe_encoded = tok_seq.ids_bpe_encoded
            _ids_no_bpe = tok_seq._ids_no_bpe

        ids_bpe_encoded = False # TODO
        _ids_no_bpe: list[int | list[int]] = None # TODO

        concat_tok_sequence = TokSequence(concat_tokens, concat_ids, concat_bytes, concat_events, ids_bpe_encoded, _ids_no_bpe) 
        # print(f"concat_tokens len={len(concat_tokens)}")
        # print(f"concat_tok_sequence len={len(concat_tok_sequence)}")
        return concat_tok_sequence
 
    def print_id(self, program):
        print(f"{program} idx={self.vocab[program]}")
 
    def token_by_id(self, id):
       return self.inv_vocab[id]
   
    def subtoksequence(self, tokens, left, right):
        subsequence_tokens = tokens.tokens[left:right]
        subsequence_ids = tokens.ids[left:right]
        subsequence_bytes: str = None
        subsequence_events: List = []
        _ids_bpe_encoded = False 
        _ids_no_bpe: List[int] = None
        return TokSequence(
            subsequence_tokens,
            subsequence_ids,
            subsequence_bytes,
            subsequence_events,
            _ids_bpe_encoded,
             _ids_no_bpe
        )


    def _tokens_to_midi(
        self,
        tokens: TokSequence,
        programs: List):
        delegate_token_sequence: List[TokSequence] = []
        if len(tokens.tokens) > 0 and tokens.tokens[0] == "BOS_None":
            tokens.tokens = tokens.tokens[1:]
            tokens.ids = tokens.ids[1:]
            tokens.events = tokens[1:]

        n = len(tokens.tokens)
        left = 0
        right = 1
        seen_programs = []

        for i, token in enumerate(tokens.tokens):
            new_token = "Program_114" if token == "Program_-1" else token
            tokens.tokens[i] = new_token

        while right < n:
          token_name = tokens.tokens[right]
          if (token_name == "Bar_0" or token_name == "Bar_None")\
            and right + 2 < n\
            and tokens.tokens[right + 1] == "Position_0"\
            and tokens.tokens[right + 2].startswith("Program_")\
            and not tokens.tokens[right + 2] in seen_programs:
                seen_programs.append(tokens.tokens[right + 2])
                while right > left\
                  and not tokens.tokens[right - 1].startswith("Duration_"):
                  right = right - 1
                subseq = self.subtoksequence(tokens, left, right)
                if len(subseq) > 0:
                  delegate_token_sequence.append(subseq)
                #   print(f"subseq={subseq.tokens[:10]}")
                #   print(f"subseq_tail={subseq.tokens[len(subseq.tokens) - 10:]}")
                #   print(f"seen_programs={seen_programs}")
                #   print()
                left = right
        #   else:
        #     print(f"tokens.tokens[right]={tokens.tokens[right]}")
        #     if right + 1 < n:
        #       print(f"tokens.tokens[right + 1]={tokens.tokens[right + 1]}")
        #     print(f"tokens.tokens[right + 2]={tokens.tokens[right + 2]}")
        #     if right + 2 < n:
            # print()
          right = right + 1
        # print(f"right={right} len={len(tokens.tokens)} left={left}")
    
        subseq = self.subtoksequence(tokens, left, right)
        # print(f"subseq={subseq.tokens[:10]}")
        # print(f"subseq_tail={subseq.tokens[len(subseq.tokens) - 10:]}")
        # print(f"seen_programs={seen_programs}")
        if len(seen_programs) < len(tokens):
            subseq_program = "Program_0"
            for token_name in tokens.tokens[left:right]:
                if token_name.startswith("Program_"):
                   subseq_program = token_name
            subseq_program = "Program_114" if subseq_program == "Program_-1" else subseq_program
            seen_programs.append(subseq_program)
        delegate_token_sequence.append(subseq)
        delegate_programs = []
        for program in seen_programs:
            program_id = int(str(program)[len("Program_"):])
            delegate_programs.append((program_id, program_id == -1)) #TODO does not work for drums
            # print(f"type={type(program_id)}")

        # self.print_id("Bar_None")
        # self.print_id("Position_0")
        # self.print_id("Program_0")

        # print(f"tokens={len(delegate_token_sequence)}")
        # print(f"programs={len(delegate_programs)}")
        # print(f"tokens={tokens.tokens[:100]}")
        # print(f"token_ids={tokens.ids[:100]}")
        return self.delegate._tokens_to_midi(delegate_token_sequence, delegate_programs)