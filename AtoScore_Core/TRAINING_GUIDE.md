# How to Train SheetSage V3 (Lunaverus) on Google Colab

Since training a deep CNN requires significant GPU power, we recommend using Google Colab Pro.

## Prerequisites
1.  **Google Account** with Colab access.
2.  **Dataset**: The [MAESTRO Dataset](https://magenta.tensorflow.org/datasets/maestro) is recommended (MIDI + Audio).

## Steps

1.  **Open Google Colab**
    *   Go to [colab.research.google.com](https://colab.research.google.com).
    *   Create a "New Notebook".

2.  **Set Runtime to GPU**
    *   Go to **Runtime** > **Change runtime type**.
    *   Select **T4 GPU** (Standard) or **A100/V100** (Pro/High-RAM).

3.  **Upload Files**
    *   Click the **Folder icon** on the left sidebar.
    *   Upload `lunaverus_cnn.py` and `train_lunaverus.py` from your `sheetsage/modules/` folder.

4.  **Install Dependencies**
    *   Run a cell with:
        ```python
        !pip install torch librosa pretty_midi numpy
        ```

5.  **Download Dataset (MAPS or Small Subset)**
    *   Since MAESTRO is very large (100GB+), you can use the **MAPS Database** (Music Audio Processing in Mono/Stereo). It is smaller and often used for transcription research.
    *   Alternatively, you can just use a **few files** to test the pipeline first.
    *   Example logic to download a smaller sample or MAPS:
        ```python
        # option 1: MAPS (Requires login typically, or find a mirror)
        # option 2: Download just ONE year of MAESTRO (Partial download)
        # e.g. 2018 is smaller:
        !wget https://storage.googleapis.com/magentadata/datasets/maestro/v3.0.0/maestro-v3.0.0-2018.zip
        # (This is hypothetical; check if partial zips exist. If not, use the MIDI-only zip + synthesize it?)
        
        # PRO TIP: Synthesize MIDI yourself!
        # 1. Download just the MIDI dataset (50MB)
        !wget https://storage.googleapis.com/magentadata/datasets/maestro/v3.0.0/maestro-v3.0.0-midi.zip
        !unzip maestro-v3.0.0-midi.zip
        
        # 2. Use FluidSynth in Colab to generate WAVs from the MIDIs.
        # This is much faster/smaller than downloading 130GB of WAVs.
        !apt-get install fluidsynth
        !cp /usr/share/sounds/sf2/FluidR3_GM.sf2 .
        # Then use a python script to render the .wav files on the fly!
        ```

6.  **Mount Google Drive (for saving weights)**
    *   Mount Drive to save your progress:
        ```python
        from google.colab import drive
        drive.mount('/content/drive')
        ```

7.  **Alternative Datasets (Full Download Guides)**

    ### Option A: MusicNet (Classical, ~20GB)
    Direct download from Zenodo (Fast & reliable).
    ```python
    !wget https://zenodo.org/record/5120004/files/musicnet.tar.gz
    !tar -xzf musicnet.tar.gz
    # Folder name will be 'musicnet'
    ```

    ### Option B: POP909 (Pop Piano, ~5GB)
    Hosted on GitHub.
    ```python
    # 1. Clone the repository structure
    !git clone https://github.com/music-x-lab/POP909-Dataset.git
    
    # 2. Download the audio files (hosted separately)
    # Note: POP909 audio is sometimes hosted on Google Drive. 
    # If direct link doesn't work, download local and upload to Drive, 
    # or use the provided script in the repo if available.
    ```
    *(Note: POP909 often requires manual audio download due to copyright hosting. Check the GitHub README.)*

    ### Option C: EMOPIA (Emotional Piano, Small)
    Hosted on Zenodo.
    ```python
    !wget https://zenodo.org/record/10013328/files/EMOPIA_1.0.zip
    !unzip -q EMOPIA_1.0.zip
    ```

8.  **Run Training**
    *   **CRITICAL**: First, check if your files are actually uploaded! Run:
        ```python
        !ls -l
        ```
        You should see `train_lunaverus.py` and `lunaverus_cnn.py`.
        If NOT, go back to the "Upload Files" step or look for where you uploaded them (e.g., inside `drive/`).
    
    *   Once verified, run the script:
        ```python
        !python train_lunaverus.py
        ```
    
    *   *Troubleshooting*:
        *   If you see `No such file or directory`, make sure you are in the folder where you uploaded the files.
        *   If you uploaded them to Drive, navigate there first:
            ```python
            %cd /content/drive/MyDrive/path/to/files/
            !python train_lunaverus.py
            ```

7.  **Download & Deploy Weights**
    *   Find `lunaverus_weights.pth` in the Colab file browser (left sidebar).
    *   Right-click -> **Download**.
    *   **Move** the file to this exact folder on your PC:
        `d:\Document\sheetsage\SheetSage_Core\sheetsage\modules\`
        
    *   **Restart SheetSage** and enjoy your new AI model!
