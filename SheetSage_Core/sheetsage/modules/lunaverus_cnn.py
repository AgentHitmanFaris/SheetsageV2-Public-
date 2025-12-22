import torch
import torch.nn as nn
import torch.nn.functional as F
import librosa
import numpy as np
import pretty_midi
import logging
import os

class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=(3, 1), padding=(1, 0)) # Freq conv
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=(1, 3), padding=(0, 1)) # Time conv
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU()
        
        # Shortcut connection handling
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
        out = self.relu(out)
        return out

class LunaverusCNN(nn.Module):
    def __init__(self):
        super(LunaverusCNN, self).__init__()
        # Input: (Batch, 1, 336, 11) -> 336 bins (88 keys * 4 bins?) + context
        # The paper/website says 4 bins per note. 88 notes * 4 = 352 bins roughly.
        # Let's standardize on 352 bins (approx 88*4) for 7 octaves + margin
        
        self.conv_entry = nn.Conv2d(1, 32, kernel_size=(5, 5), padding=(2, 2))
        self.bn_entry = nn.BatchNorm2d(32)
        self.relu = nn.ReLU()
        
        self.layer1 = self._make_layer(32, 32, 2)
        self.pool1 = nn.MaxPool2d(kernel_size=(2, 1)) # Pool freq only to maintain time resolution? Or both?
        # Website says pool after some layers.
        
        self.layer2 = self._make_layer(32, 64, 2)
        self.pool2 = nn.MaxPool2d(kernel_size=(2, 1))
        
        self.layer3 = self._make_layer(64, 128, 2)
        
        # Final classification layers (No Dense, Fully Convolutional style)
        # We need to map down to 88 keys.
        # Current Freq Dim after pools: (Original / 4).
        
        # Global Average Pool over Time (for the specific window slice)
        # Or just conv down to 1x1 if the input is fixed size?
        # Lunaverus takes "slices". Let's assume input is (B, 1, Freq, TimeWindow)
        
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))
        self.flatten = nn.Flatten()
        self.fc_final = nn.Linear(128, 88)
        
    def _make_layer(self, in_channels, out_channels, blocks):
        layers = []
        layers.append(ResidualBlock(in_channels, out_channels))
        for _ in range(1, blocks):
            layers.append(ResidualBlock(out_channels, out_channels))
        return nn.Sequential(*layers)

    def forward(self, x):
        # x: (Batch, 1, Freq, Time)
        out = self.relu(self.bn_entry(self.conv_entry(x)))
        out = self.layer1(out)
        out = self.pool1(out)
        out = self.layer2(out)
        out = self.pool2(out)
        out = self.layer3(out)
        
        out = self.global_pool(out)
        out = self.flatten(out)
        out = self.fc_final(out)
        return torch.sigmoid(out)

def compute_cqt(audio_path, sr=22050):
    """
    Computes Log-Amplitude CQT.
    """
    try:
        y, _ = librosa.load(audio_path, sr=sr)
        # CQT parameters based on Lunaverus description (4 bins/note)
        hop_length = 512
        n_bins = 88 * 4 # 352 bins
        bins_per_octave = 48 # 12 * 4
        fmin = librosa.note_to_hz('A0')
        
        C = librosa.cqt(y, sr=sr, fmin=fmin, n_bins=n_bins, bins_per_octave=bins_per_octave, hop_length=hop_length)
        C_db = librosa.amplitude_to_db(np.abs(C), ref=np.max)
        
        # Normalize roughly to 0-1 range for NN
        C_norm = (C_db + 80.0) / 80.0
        C_norm = np.clip(C_norm, 0, 1)
        
        return C_norm, hop_length # (Freq, Time)
    except Exception as e:
        print(f"CQT Error: {e}")
        return None, None

def run_lunaverus(audio_path, model_weights_path=None, device='cpu'):
    """
    Runs the full inference pipeline.
    """
    print(f"Running SheetSage V3 (Lunaverus) on {audio_path}")
    
    # 1. Load Model
    model = LunaverusCNN().to(device)
    if model_weights_path and os.path.exists(model_weights_path):
        try:
            model.load_state_dict(torch.load(model_weights_path, map_location=device))
            print("Loaded trained weights.")
        except Exception as e:
            print(f"Failed to load weights: {e}")
    else:
        print("WARNING: Running with initialized (random) weights for demonstration.")
    
    model.eval()
    
    # 2. Preprocess
    cqt_spec, hop_length = compute_cqt(audio_path)
    if cqt_spec is None:
        return None
        
    # 3. Create Inputs (Slicing)
    # We slice the spectrogram into windows to feed the CNN
    # Window size: let's pick 11 frames (~0.25s) context
    # 3. Create Inputs (Optimized Slicing)
    window_size = 11 
    half_window = window_size // 2
    
    # Pad frequency axis if needed? No, usually pads time axis.
    # Input CQT shape: (Freq, Time)
    # We want to slide over Time.
    # Pads: (0,0) for Freq, (half, half) for Time.
    cqt_padded = np.pad(cqt_spec, ((0, 0), (half_window, half_window)), mode='constant')
    
    # Use PyTorch Unfold for fast sliding window
    # Tensor shape: (1, 1, Freq, Time+Pad)
    inp = torch.tensor(cqt_padded, dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(device)
    
    # Unfold along last dimension (Time)
    # shape: (1, 1, Freq, Time) -> unfold(dimension, size, step)
    # We unfold dimension 3 (Time).
    # Since we want a 2D window (Freq x Window), but Freq is full height?
    # Architecture expects (Batch, 1, Freq, Window).
    # Unfold dimension 3: results in (1, 1, Freq, NumWindows, WindowSize).
    
    # Actually, simpler: Treat columns as features?
    # No, CNN convolves over time and freq.
    
    # Unfolding:
    # input: (Batch, Channel, Height, Width)
    # We want to extract patches of size (Freq, WindowSize).
    # F.unfold extracts patches.
    # But F.unfold flattens the patches.
    # Let's use simple indexing with stride tricks if numpy, or just loop with larger batches if naive loop is bottle neck.
    # Unfold on 1D is easier.
    
    # Let's try `unfold` on the time dimension.
    # input: (1, Freq, Time)
    inp_sq = inp.squeeze(1) # (1, Freq, Time)
    # Unfold dimension 2 (Time)
    # Result: (1, Freq, NumWindows, WindowSize)
    windows = inp_sq.unfold(2, window_size, 1) # (1, Freq, NumWindows, Window)
    
    # Permute to (NumWindows, 1, Freq, Window)
    # steps: (1, Freq, N, W) -> (N, Freq, W) -> (N, 1, Freq, W)
    windows = windows.permute(2, 0, 1, 3) # (NumWindows, 1, Freq, Window)
    
    num_windows = windows.shape[0]
    
    # 4. Run Inference in Batches
    batch_size = 512
    all_probs = []
    
    print(f"Running inference on {num_windows} frames (Batch Size: {batch_size})...")
    
    with torch.no_grad():
        for i in range(0, num_windows, batch_size):
            batch = windows[i : i + batch_size] # (B, 1, Freq, Window)
            out = model(batch)
            all_probs.append(out.cpu().numpy())
            
    # Concatenate all probabilities
    probs = np.concatenate(all_probs, axis=0) # (NumFrames, 88)
    
    # 5. Note Decoding (Merge consecutive frames)
    # Frame-wise probs: (Time, 88)
    threshold = 0.5
    
    midi = pretty_midi.PrettyMIDI()
    piano = pretty_midi.Instrument(program=0)
    
    # Transpose to (88, Time) for easier per-key processing
    probs_T = probs.T 
    
    for key_idx in range(88):
        key_probs = probs_T[key_idx]
        is_active = key_probs > threshold
        
        # Find runs of True
        diff = np.diff(is_active.astype(int))
        starts = np.where(diff == 1)[0] + 1
        ends = np.where(diff == -1)[0] + 1
        
        # Handle edge cases (starts active, ends active)
        if is_active[0]:
            starts = np.insert(starts, 0, 0)
        if is_active[-1]:
            ends = np.append(ends, len(is_active))
            
        for s, e in zip(starts, ends):
            # Filter short notes? (e.g. < 5 frames)
            if e - s < 3: continue 
            
            start_time = s * hop_length / 22050.0
            end_time = e * hop_length / 22050.0
            pitch = key_idx + 21
            
            note = pretty_midi.Note(
                velocity=100,
                pitch=int(pitch),
                start=start_time,
                end=end_time
            )
            piano.notes.append(note)

    midi.instruments.append(piano)
    
    # Define output path
    output_dir = os.path.dirname(audio_path)
    output_midi = os.path.join(output_dir, "lunaverus_output.midi")
    midi.write(output_midi)
    
    print(f"Inference Complete. Generated {len(piano.notes)} notes.")
    return output_midi

run_inference = run_lunaverus
