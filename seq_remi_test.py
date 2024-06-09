from scripts.tokenizers import SeqREMI
from miditok import REMI, MIDILike, TokenizerConfig
from symusic import Score


def main():
    print("hi")
    input_file = "/home/kliffeup/gutsolksenia/Neuromusic/test_results_custom/compositions/1/midi//1.mid"
    out_file = "/home/kliffeup/gutsolksenia/Neuromusic/test_results_custom/compositions/1/midi/test.mid"
    tokenizer_config = TokenizerConfig(
        num_velocities=16, 
        use_chords=True, 
        use_programs=True, 
        remove_duplicated_notes=True, 
        delete_equal_successive_tempo_changes=True,
        delete_equal_successive_time_sig_changes=True
    )
    tokenizer = SeqREMI(tokenizer_config=tokenizer_config)
    tokens = tokenizer(Score(input_file))
    # print(f"tokens={tokens.tokens[:100]}")
    # print(f"token_ids={tokens.ids[:100]}")
    tokenizer(tokens).dump_midi(out_file)

if __name__ == "__main__":
    main()