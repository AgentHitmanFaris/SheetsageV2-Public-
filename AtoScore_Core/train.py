import argparse
import logging
import random
import sys
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

# Import project modules
from sheetsage.modules import EncOnlyTransducer, TransformerEncoder
from sheetsage.infer import (
    InputFeats, Task,
    _INPUT_TO_DIM, _TASK_TO_VOCAB_SIZE, _MAX_TERTIARIES_PER_CHUNK
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DummyDataset(Dataset):
    """
    Generates dummy data for testing the training loop.
    """
    def __init__(self, length=100):
        self.length = length
        self.src_dim = _INPUT_TO_DIM[InputFeats.HANDCRAFTED]
        self.vocab_size = _TASK_TO_VOCAB_SIZE[Task.MELODY]
        self.max_len = _MAX_TERTIARIES_PER_CHUNK

    def __len__(self):
        return self.length

    def __getitem__(self, idx):
        # Random sequence length
        seq_len = random.randint(32, self.max_len)

        # Random features: (seq_len, feature_dim)
        features = torch.randn(seq_len, self.src_dim)

        # Random targets: (seq_len,)
        targets = torch.randint(0, self.vocab_size, (seq_len,))

        return features, targets

def collate_fn(batch):
    """
    Pads batch of variable length sequences.
    """
    features, targets = zip(*batch)

    # Get lengths
    lengths = torch.tensor([f.size(0) for f in features])
    max_len = max(lengths)

    # Pad features
    feature_dim = features[0].size(1)
    padded_features = torch.zeros(len(features), max_len, feature_dim)
    for i, f in enumerate(features):
        padded_features[i, :lengths[i], :] = f

    # Pad targets
    padded_targets = torch.zeros(len(targets), max_len, dtype=torch.long)
    for i, t in enumerate(targets):
        padded_targets[i, :lengths[i]] = t

    # Transpose features to (max_len, batch, dim) as expected by model
    padded_features = padded_features.transpose(0, 1)

    # Targets usually expected as (max_len, batch) or (batch, max_len) depending on loss
    # Model returns (max_len, batch, vocab_size)
    padded_targets = padded_targets.transpose(0, 1)

    return padded_features, lengths, padded_targets

def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logging.info(f"Using device: {device}")

    # Initialize Model
    output_dim = _TASK_TO_VOCAB_SIZE[Task.MELODY]
    src_dim = _INPUT_TO_DIM[InputFeats.HANDCRAFTED]

    # Using Transformer config similar to inference
    model = EncOnlyTransducer(
        output_dim,
        src_emb_mode="project",
        src_vocab_size=None,
        src_dim=src_dim,
        src_emb_dim=512,
        src_pos_emb=True, # Assuming pos emb used
        src_dropout_p=0.1,
        enc_cls=TransformerEncoder,
        enc_kwargs={
            "model_dim": 512,
            "num_heads": 8,
            "num_layers": 4, # Using smaller model for example
            "feedforward_dim": 2048,
            "dropout_p": 0.1,
        },
    )
    model.to(device)

    # Dataset and DataLoader
    if args.dummy:
        dataset = DummyDataset()
    else:
        logging.error("Real dataset loading not fully implemented in this script yet. Use --dummy.")
        sys.exit(1)

    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, collate_fn=collate_fn)

    # Optimizer and Loss
    optimizer = optim.Adam(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss(ignore_index=0) # Assuming 0 is padding/silence if needed, checkvocab

    # Training Loop
    model.train()
    for epoch in range(args.epochs):
        total_loss = 0
        for batch_idx, (features, lengths, targets) in enumerate(dataloader):
            features = features.to(device)
            lengths = lengths.to(device)
            targets = targets.to(device)

            optimizer.zero_grad()

            # Forward pass
            # Model forward: (src, src_len, tgt=None, tgt_len=None)
            output = model(features, lengths)

            # Output shape: (max_len, batch, vocab_size)
            # Targets shape: (max_len, batch)

            # Flatten for loss calculation
            output_flat = output.view(-1, output_dim)
            targets_flat = targets.reshape(-1)

            loss = criterion(output_flat, targets_flat)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

            if batch_idx % 10 == 0:
                logging.info(f"Epoch {epoch+1}/{args.epochs}, Batch {batch_idx}, Loss: {loss.item():.4f}")

        avg_loss = total_loss / len(dataloader)
        logging.info(f"Epoch {epoch+1} complete. Average Loss: {avg_loss:.4f}")

    # Save model
    if args.save_path:
        torch.save(model.state_dict(), args.save_path)
        logging.info(f"Model saved to {args.save_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Sheet Sage Model")
    parser.add_argument("--dummy", action="store_true", help="Use dummy dataset for testing")
    parser.add_argument("--epochs", type=int, default=2, help="Number of epochs")
    parser.add_argument("--batch_size", type=int, default=4, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--save_path", type=str, default="model.pth", help="Path to save model")

    args = parser.parse_args()

    train(args)
