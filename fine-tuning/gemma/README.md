## Code
- `common.py`: Initialises container images and configs for `train.py` and `inference.py`
- `train.py`: Code to fine-tune.
  - `main` function is the local entrypoint that runs locally. It triggers and calls the other functions to run on modal.
- `<model>-config.yml`: The `axolotl` configuration to fine-tune Gemma-2 9B.
  - `datasets` key: Defines the path to the dataset, how to read it and the format in which to construct it. This is custom. Other examples [here](https://github.com/axolotl-ai-cloud/axolotl/tree/main/examples/).
  - `train_on_inputs` key: Defines whether to mask the input while fine-tuning, set to `false`. Comparision of performance between `true`/`false` maybe interesting
  - `seed` key: For reproducability
  - `num_epochs` key: Comparision of performance on different epochs maybe interesting.
  - `dataset_prepared_path`: Where to prep and save dataset. *Might break if changed.*
  - `output_dir`: Which directory to output the lora adapter. *Note: Changing this will break `calculate_perplexity.py` because it reads and loads the model from here.*
  - Weight and Biases config: Recomended to add the w&b project here for visibility during the training run!

- `data.subsample.jsonl`: Subsample of training data. **Use this to overfit and check the training code works!**

- `data.jsonl`: Training data.

- `<model>-dataset.ipynb`: Notebook to read through and create the training dataset.

- `calculate_perplexity.py`: Standalone Modal Function to load the model and return perplexity scores on the inputs. *Input: `data.jsonl` with `output` key present; `run_name` of the training run.*
  - Might be needed to modify to write the scores to a file or whatever.
## Running

### Data Prep
Run the `<model>-dataset.ipynb` notebook

### Fine-tuning

```bash
GPU_CONFIG= ALLOW_WANDB=false modal run train --config=<model>-config.yml --data=data.jsonl
```

- `GPU_CONFIG` env can be ignored. Default works.
- `ALLOW_WANDB=true` needed if weight and biases is being used.
- `--config`: set to axolotl config file
- Optional: `--detach` to run in detached mode


### Inference
```bash
modal run -q inference --run-name <run_name>
```

- `-q` recommended.
- `--run-name`: Defaults to latest run if not specified


### Perplexity Scores
```bash
modal run calculate_perplexity
```
