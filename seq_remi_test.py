from scripts.tokenizers import SeqREMI
from miditok import REMI, MIDILike, TokenizerConfig
from symusic import Score


def main():
    print("hi")
    input_file = "/home/kliffeup/gutsolksenia/Neuromusic/test_results_custom/2/original.mid"
    out_file = "/home/kliffeup/gutsolksenia/Neuromusic/test_results_custom/2/result.mid"
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
    tokenizer(tokens).dump_midi(out_file)

if __name__ == "__main__":
    main()