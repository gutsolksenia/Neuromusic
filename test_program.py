import argparse
import json
import os
from pathlib import Path

import torch
# from miditok.midi_tokenizer import MIDITokenizer
from tqdm import tqdm

import scripts.model as module_model
from scripts.converter import Converter
from scripts.generator import ProgramGenerator
from scripts.trainer import Trainer
from scripts.utils import DATA_PATH
from scripts.utils.object_loading import get_dataloaders
from scripts.utils.parse_config import ConfigParser

DEFAULT_CHECKPOINT_PATH = DATA_PATH / "default_test_model" / "checkpoint.pth"


def main(
    config, 
    out_path
):
    logger = config.get_logger("test")

    # define cpu or gpu if possible
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # test_encoder
    tokenizer = config.get_midi_encoder()
    logger.info(f"tokenizer={type(tokenizer)}") 

    # setup data_loader instances
    dataloaders = get_dataloaders(config, tokenizer)

    # build model architecture
    model = config.init_obj(
        config["arch"], 
        module_model, 
        n_class=len(tokenizer), 
        pad_id=tokenizer["PAD_None"]
    )
    logger.info(model)

    logger.info("Loading checkpoint: {} ...".format(config.resume))
    checkpoint = torch.load(config.resume, map_location=device)
    state_dict = checkpoint["state_dict"]
    if config["n_gpu"] > 1:
        model = torch.nn.DataParallel(model)
    model.load_state_dict(state_dict)

    # prepare model for testing
    model = model.to(device)
    model.eval()

    results = []
    generator = ProgramGenerator(model, tokenizer=tokenizer, device=device, sample=True)
    output_dir = Path(out_path)
    with torch.no_grad():
        for batch_idx, batch in enumerate(tqdm(dataloaders["test"])):
            batch = Trainer.move_batch_to_device(batch, device)
            for item_idx in range(batch['input_ids'].shape[0]):
                midi_path = batch['midi_path'][item_idx]
                original = batch['input_ids'][item_idx].cpu().detach()
                generated = generator.continue_seq(original).cpu().detach()
                continued_original = torch.cat([original, generated], dim=-1).cpu().detach()
                
                name = Path(midi_path).stem
                item_path = output_dir / 'compositions' / name
                # item_audio_path = item_path / 'audio'
                item_midi_path = item_path / 'midi'
                # os.makedirs(item_audio_path, exist_ok=True)
                os.makedirs(item_midi_path, exist_ok=True)
                
                # converter.score_to_audio(tokenizer(generated), str(item_audio_path / 'generated.wav'))
                # converter.score_to_audio(tokenizer(original), str(item_audio_path / 'original.wav'))
                # converter.score_to_audio(tokenizer(continued_original), str(item_audio_path / 'continued_original.wav'))

                tokenizer(generated).dump_midi(str(item_midi_path / 'generated.midi'))
                tokenizer(original).dump_midi(str(item_midi_path / 'original.midi'))
                tokenizer(continued_original).dump_midi(str(item_midi_path / 'continued_original.midi'))

                results.append({
                    'composition_dir': str(item_path.absolute()),
                    'generated_length': generated.shape[0],
                    'original_length': original.shape[0],
                    'continued_original_length': continued_original.shape[0],
                    'ended_with_eos': tokenizer['EOS_None'] in list(generated),
                })

    with open(output_dir / 'results.json', 'w') as fp:
        json.dump(results, fp, indent=2)


# def save_tokens(tokens: torch.Tensor, dir: Path, name: str, tokenizer: MIDITokenizer, converter: Converter):
#     score = tokenizer(tokens)
#     midi_path = dir / 'midi' / 'name.midi'
#     # converter.score_to_audio()



if __name__ == "__main__":
    args = argparse.ArgumentParser(description="PyTorch Template")
    args.add_argument(
        "-c",
        "--config",
        default=None,
        type=str,
        help="config file path (default: None)",
    )
    args.add_argument(
        "-r",
        "--resume",
        default=str(DEFAULT_CHECKPOINT_PATH.absolute().resolve()),
        type=str,
        help="path to latest checkpoint (default: None)",
    )
    args.add_argument(
        "-d",
        "--device",
        default=None,
        type=str,
        help="indices of GPUs to enable (default: all)",
    )
    args.add_argument(
        "-o",
        "--output",
        default="output.json",
        type=str,
        help="File to write results (.json)",
    )
    args.add_argument(
        "-t",
        "--test-data-folder",
        default=None,
        type=str,
        help="Path to dataset",
    )
    args.add_argument(
        "-b",
        "--batch-size",
        default=20,
        type=int,
        help="Test dataset batch size",
    )
    args.add_argument(
        "-j",
        "--jobs",
        default=1,
        type=int,
        help="Number of workers for test dataloader",
    )
    args.add_argument(
        "--continue_length",
        default=1024,
        type=int,
        help="Number of tokens to generate",
    )

    args = args.parse_args()

    # set GPUs
    if args.device is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = args.device

    # first, we need to obtain config with model parameters
    # we assume it is located with checkpoint in the same folder
    model_config = Path(args.resume).parent / "config.json"
    with model_config.open() as f:
        config = ConfigParser(json.load(f), resume=args.resume)

    # update with addition configs from `args.config` if provided
    if args.config is not None:
        with Path(args.config).open() as f:
            config.config.update(json.load(f))

    # if `--test-data-folder` was provided, set it as a default test set
    if args.test_data_folder is not None:
        test_data_folder = Path(args.test_data_folder).absolute().resolve()
        assert test_data_folder.exists()
        config.config["data"] = {
            "test": {
                "batch_size": args.batch_size,
                "num_workers": args.jobs,
                "datasets": [
                    {
                        "type": "CustomDirAudioDataset",
                        "args": {
                            "audio_dir": str(test_data_folder),
                            "full_audio": True
                        },
                    }
                ],
            }
        }

    assert config.config.get("data", {}).get("test", None) is not None
    config["data"]["test"]["batch_size"] = args.batch_size
    config["data"]["test"]["n_jobs"] = args.jobs
    main(config, args.output)
