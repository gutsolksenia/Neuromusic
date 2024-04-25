from miditok import REMI, TokenizerConfig, TokSequence
from typing import List
import copy

class SeqREMI(REMI):
    def __init__(self, tokenizer_config: TokenizerConfig, *args, **kwargs):
        parent_config:TokenizerConfig = copy.deepcopy(tokenizer_config)
        parent_config.one_token_stream_for_programs = False
        super().__init__(parent_config, *args, **kwargs)
    
    def _midi_to_tokens(self, *args, **kwargs) -> TokSequence:
        # print("_midi_to_tokens")
        parent_tokens: List[TokSequence] = super()._midi_to_tokens(*args, **kwargs)
        concat_tokens: List[str] = []
        concat_ids: List[int] = []
        concat_bytes: str = None
        concat_events: List = []
        ids_bpe_encoded = False 
        _ids_no_bpe: List[int] = None

        # print(f"got {len(parent_tokens)} programs")
        for tok_seq in parent_tokens:
            concat_tokens.extend(tok_seq.tokens)
            concat_ids.extend(tok_seq.ids)
            # print(f"tok_seq len={len(tok_seq)}")
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
 
    def _tokens_to_midi(
        self,
        tokens: TokSequence,
        programs: List):
        print(f"voc={self.vocab}")
        super()._tokens_to_midi(tokens, programs)