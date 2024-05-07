from miditok import REMI, TokenizerConfig, TokSequence
from typing import List
import copy

class SeqREMI(REMI):

    def __init__(self, tokenizer_config: TokenizerConfig, max_bar_embedding=N, *args, **kwargs):
        super().__init__(tokenizer_config, max_bar_embedding=max_bar_embedding, *args, **kwargs)
        delegate_config:TokenizerConfig = copy.deepcopy(tokenizer_config)
        delegate_config.one_token_stream_for_programs = False
        self.delegate = REMI(delegate_config, max_bar_embedding=max_bar_embedding, *args, **kwargs)
        # print(f"self.tokens={self.vocab}")
        # print(f"delegate.tokens={self.delegate.vocab}")

    
    def _midi_to_tokens(self, *args, **kwargs) -> TokSequence:
        # print("_midi_to_tokens")
        delegate_tokens: List[TokSequence] = self.delegate._midi_to_tokens(*args, **kwargs)
        concat_tokens: List[str] = []
        concat_ids: List[int] = []
        concat_bytes: str = None
        concat_events: List = []
        ids_bpe_encoded = False 
        _ids_no_bpe: List[int] = None

        # print(f"got {len(parent_tokens)} programs")
        for tok_seq in delegate_tokens:
            concat_tokens.extend(tok_seq.tokens)
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
        

        n = len(tokens.tokens)
        left = 0
        right = 1

        print(f"programs={programs}")
        while right < n:
          token_name = tokens.tokens[right]
          if (token_name == "Bar_0" or token_name == "Bar_None")\
            and right + 2 < n\
            and tokens.tokens[right + 1] == "Position_0"\
            and tokens.tokens[right + 2].startswith("Program_"):
                subseq = self.subtoksequence(tokens, left, right)
                # print(f"subseq={subseq}")
                delegate_token_sequence.append(subseq)
          right = right + 1
        # print(f"subseq={subseq}")
        subseq = self.subtoksequence(tokens, left, right)
        delegate_token_sequence.append(subseq)
               
        # self.print_id("Bar_None")
        # self.print_id("Position_0")
        # self.print_id("Program_0")

        return self.delegate._tokens_to_midi(delegate_token_sequence, programs)