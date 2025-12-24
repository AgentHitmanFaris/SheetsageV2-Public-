# Sheet Sage Model Training

This document explains the model architecture, data pipeline, and training process for Sheet Sage.

## 1. Model Architecture

Sheet Sage uses a Transformer-based architecture for transcription tasks (Melody and Harmony). The core model class is `EncOnlyTransducer` defined in `atoscore/modules/modules.py`.

### Key Components:

*   **Encoder**: A standard Transformer Encoder (`TransformerEncoder`) is used to process the input features.
    *   **Input**: Beat-aligned audio features (Log-Mel Spectrograms).
    *   **Architecture**: Multi-head self-attention layers with feedforward networks.
    *   **Configuration**: Typically 6 layers, 8 heads, 512 model dimension (as seen in `atoscore/infer.py` and `train.py`).

*   **Projection**:
    *   **Input Projection**: Input features (dimension 229 for Handcrafted features) are projected to the model dimension (512).
    *   **Output Projection**: The encoder output is projected to the vocabulary size (89 for Melody, 97 for Harmony).

*   **Positional Embeddings**: Sinusoidal positional embeddings are added to the input embeddings to retain sequence order information.

## 2. Data Pipeline

The data handling logic is located in `atoscore/data.py`.

### Data Source: Hooktheory
The primary dataset used is the **Hooktheory** dataset, which provides high-quality user-contributed lead sheets.

*   **MelodyTranscriptionExample**: This class represents a single training example. It contains:
    *   `segment_start` / `segment_end`: Time boundaries of the segment.
    *   `melody`: A list of `Note` objects (onset, pitch, offset).
    *   `beat_times`: Timestamps of beats, essential for aligning audio features to the musical grid.

### Feature Extraction
Audio is processed into Log-Mel Spectrograms using `atoscore/representations/handcrafted.py`.
*   **Sample Rate**: 16kHz
*   **Mel Bands**: 229
*   **Hop Size**: 512 samples

During training (and inference), these features are **beat-aligned**. This means the raw spectrogram frames are resampled to a fixed number of "tertiaries" (sub-beats) per beat (default is 4 tertiaries per beat, i.e., 16th notes).

## 3. Training Process

The training logic is implemented in `train.py`.

### Optimizer & Loss
*   **Optimizer**: Adam (`torch.optim.Adam`) with a default learning rate of 1e-4.
*   **Loss Function**: Cross Entropy Loss (`nn.CrossEntropyLoss`).
    *   The model predicts a token for each time step (tertiary).
    *   `ignore_index=0` is used to handle padding or silence if necessary.

### How to Run Training

A `train.py` script is provided to start training. By default, it runs with a dummy dataset to verify the setup.

#### Prerequisite
Ensure dependencies are installed:
```bash
pip install -r requirements.txt
```

#### Running with Dummy Data
To verify the training loop works:
```bash
python train.py --dummy --epochs 5 --batch_size 4
```

#### Command Line Arguments
*   `--dummy`: Use generated dummy data instead of real data.
*   `--epochs`: Number of training epochs (default: 2).
*   `--batch_size`: Batch size (default: 4).
*   `--lr`: Learning rate (default: 1e-4).
*   `--save_path`: Path to save the trained model weights (default: `model.pth`).

### Future Work: Training on Real Data
To train on the full Hooktheory dataset:
1.  Implement a specific `Dataset` class in `train.py` that utilizes `atoscore.data.iter_hooktheory`.
2.  Ensure you have access to the Hooktheory dataset assets (managed via `atoscore/assets.py`).
3.  Update `train.py` to load this dataset when `--dummy` is not specified.

