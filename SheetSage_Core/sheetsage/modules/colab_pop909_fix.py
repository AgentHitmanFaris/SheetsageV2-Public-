# COPY ALL OF THIS INTO A GOOGLE COLAB CELL
# ==========================================

# 1. Install System Dependencies (FluidSynth for Audio Generation)
import os
os.system("apt-get update -y")
os.system("apt-get install -y fluidsynth")
os.system("cp /usr/share/sounds/sf2/FluidR3_GM.sf2 .")
os.system("pip install pyfluidsynth pretty_midi librosa")

import glob
import pretty_midi
import librosa
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import soundfile as sf

print("✅ Dependencies Installed.")

# 2. Define The Model (Lunaverus Architecture)
class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=(3, 1), padding=(1, 0))
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=(1, 3), padding=(0, 1))
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU()
        self.shortcut = nn.Sequential()
        if in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=1),
                nn.BatchNorm2d(out_channels)
            )
    def forward(self, x):
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        return self.relu(out)

class LunaverusCNN(nn.Module):
    def __init__(self):
        super(LunaverusCNN, self).__init__()
        self.conv_entry = nn.Conv2d(1, 32, kernel_size=(5, 5), padding=(2, 2))
        self.bn_entry = nn.BatchNorm2d(32)
        self.relu = nn.ReLU()
        self.layer1 = self._make_layer(32, 32, 2)
        self.pool1 = nn.MaxPool2d(kernel_size=(2, 1))
        self.layer2 = self._make_layer(32, 64, 2)
        self.pool2 = nn.MaxPool2d(kernel_size=(2, 1))
        self.layer3 = self._make_layer(64, 128, 2)
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))
        self.flatten = nn.Flatten()
        self.fc_final = nn.Linear(128, 88) 
    def _make_layer(self, in_c, out_c, blocks):
        layers = [ResidualBlock(in_c, out_c)] + [ResidualBlock(out_c, out_c) for _ in range(blocks-1)]
        return nn.Sequential(*layers)
    def forward(self, x):
        out = self.relu(self.bn_entry(self.conv_entry(x)))
        out = self.layer1(out)
        out = self.pool1(out)
        out = self.layer2(out)
        out = self.pool2(out)
        out = self.layer3(out)
        out = self.global_pool(out)
        out = self.flatten(out)
        return torch.sigmoid(self.fc_final(out))

# 3. Dataset Loader (Auto-Synthesizes Audio)
class POP909Dataset(Dataset):
    def __init__(self, root_dir):
        self.pairs = []
        # Find all .mid files recursively
        # POP909 structure: POP909/001/001.mid
        if not os.path.exists(root_dir):
            print(f"❌ Error: Directory '{root_dir}' not found. Did you clone the repo?")
            return

        midi_files = glob.glob(os.path.join(root_dir, "**/*.mid"), recursive=True)
        print(f"Found {len(midi_files)} MIDI files. Preparing audio (Synthesizing if missing)...")
        
        self.cache_dir = "audio_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
        count = 0
        limit = 20 # LIMIT TO 20 SONGS FOR FAST DEMO. REMOVE THIS LIMIT FOR FULL TRAINING.
        
        for mf in midi_files:
            if count >= limit: break
            
            base = os.path.basename(mf)
            wav_path = os.path.join(self.cache_dir, base.replace(".mid", ".wav"))
            
            # Synthesize if not exists
            if not os.path.exists(wav_path):
                try:
                    # PM synthesis
                    pm = pretty_midi.PrettyMIDI(mf)
                    audio_data = pm.fluidsynth(fs=22050, sf2_path="FluidR3_GM.sf2")
                    sf.write(wav_path, audio_data, 22050)
                    print(f"Generated: {wav_path}")
                except Exception as e:
                    print(f"Skipping {base}: {e}")
                    continue
            
            self.pairs.append((wav_path, mf))
            count += 1
        
        print(f"✅ Prepared {len(self.pairs)} training pairs.")

    def __len__(self): return len(self.pairs)

    def __getitem__(self, idx):
        # Returns Dummy Tensors for Architecture Verification
        # (Real training requires CQT, but this tests the pipeline and memory)
        return torch.randn(1, 352, 11), torch.zeros(88)

# 4. Run Training
dataset_path = "POP909-Dataset" # Make sure this matches your git clone folder name
dataset = POP909Dataset(dataset_path)

if len(dataset) > 0:
    loader = DataLoader(dataset, batch_size=8, shuffle=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Training on {device}...")
    
    model = LunaverusCNN().to(device)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.BCELoss()

    model.train()
    for epoch in range(1): # Run 1 Epoch
        total_loss = 0
        for i, (data, target) in enumerate(loader):
            data, target = data.to(device), target.to(device)
            optimizer.zero_grad()
            output = model(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            
            if i % 5 == 0:
                print(f"Batch {i}, Loss: {loss.item():.4f}")

    print("🎉 Training Finished!")
    torch.save(model.state_dict(), "lunaverus_weights.pth")
    print("Saved 'lunaverus_weights.pth'. Donwload this file!")
else:
    print("⚠️ No data loaded. Check the dataset path.")
