import os
import subprocess
import logging
import pathlib
import uuid

def run_omnizart(audio_path, output_dir_str, mode="drum", callback=None):
    """
    Runs Omnizart transcription using the 'omnizart_env' located in the project root.
    
    Args:
        audio_path (str): Path to the input audio file.
        output_dir_str (str): Path to the output directory.
        mode (str): Transcription mode. Options: 'music', 'chord', 'drum', 'vocal', 'vocal-contour', 'beat'.
        
    Returns:
        str: Path to the generated output file (usually MIDI), or None if failed.
    """
    import time
    import threading

    # Timer logic
    start_time = time.time()
    stop_event = threading.Event()

    def timer_loop():
        while not stop_event.is_set():
            elapsed = int(time.time() - start_time)
            # Print to console with carriage return to show aliveness without spamming too much
            # Sys.stderr is good for unbuffered status
            if elapsed > 0 and elapsed % 2 == 0: # Every 2s
                print(f"[Omnizart Timer] Elapsed: {elapsed}s...", end='\r', flush=True)
            time.sleep(1)

    try:
        # 1. Resolve Paths
        project_root = pathlib.Path(os.getcwd())
        env_path = project_root / "omnizart_env"
        
        # Check if env exists
        if not env_path.exists():
            # Try parent directory
            env_path = project_root.parent / "omnizart_env"
            if not env_path.exists():
                logging.error(f"Omnizart environment not found at {env_path}")
                print(f"Error: 'omnizart_env' folder not found at {project_root / 'omnizart_env'} or {env_path}")
                return None
            else:
                logging.info(f"Found omnizart_env at {env_path}")

        # Executable path (Windows)
        python_exe = env_path / "Scripts" / "python.exe"
        
        if not python_exe.exists():
            logging.error(f"Python executable not found at {python_exe}")
            print(f"Error: Python executable not found at {python_exe}")
            return None
            
        # Ensure output dir exists
        output_dir = pathlib.Path(output_dir_str)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. Build Command
        # Add CUDA 11.0 path for Omnizart (it needs cudart64_110.dll)
        py_cmd = (
            "import tensorflow as tf; "
            "print('\\n[Omnizart Wrapper] Tensor Device: ' + str(tf.config.list_physical_devices('GPU') or 'CPU Only') + '\\n'); "
            "from omnizart.cli.cli import entry; "
            "entry()"
        )

        cmd = [
            str(python_exe),
            "-c",
            py_cmd,
            mode,
            "transcribe",
            str(audio_path),
            "-o",
            str(output_dir)
        ]
        
        print(f"Running Omnizart ({mode}) subprocess...")
        
        # 3. Execute with Popen
        # Add CUDA 11.2 libs to PATH for this subprocess
        env = os.environ.copy()
        cuda_112_path = pathlib.Path(os.getcwd()) / "cuda_libs"
        if cuda_112_path.exists():
            env['PATH'] = str(cuda_112_path) + os.pathsep + env.get('PATH', '')
            print(f"Added CUDA 11.2 path: {cuda_112_path}")
        else:
            # Fallback to CPU if libs not found
            env['CUDA_VISIBLE_DEVICES'] = ''
            print(f"CUDA libs not found, using CPU mode")
        
        # Start timer
        t_thread = threading.Thread(target=timer_loop, daemon=True)
        t_thread.start()

        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            text=True, 
            bufsize=1, 
            universal_newlines=True,
            env=env  # Use modified environment
        )

        # Stream output
        last_update = 0
        for line in process.stdout:
            line = line.strip()
            if not line: continue
            
            # Print to console (preserving the timer effect? simple print is fine, it just pushes timer up)
            print(f"[{mode.upper()}] {line}")
            
            # Update Gradio via callback
            if callback:
                # Basic heuristic to extract percentage if available
                # Omnizart often uses tqdm style bars: "10%|#   | 100/1000"
                # We can just show the last line as desc
                try:
                    # Don't update too aggressively to prevent UI lag
                    now = time.time()
                    if now - last_update > 0.5 or "%" in line:
                        clean_msg = line[:60] + "..." if len(line) > 60 else line
                        callback(clean_msg)
                        last_update = now
                except:
                    pass

        process.wait()
        stop_event.set()
        t_thread.join(timeout=1.0)
        
        print(f"\nOmnizart finished in {int(time.time() - start_time)}s.")
        
        if process.returncode != 0:
            logging.error(f"Omnizart process returned non-zero exit code: {process.returncode}")
            if process.returncode == 3221226505:
                print("Error: Exit code 3221226505 detected. This usually indicates a missing 'zlibwapi.dll' required by cuDNN.")
            return None
            
        # 4. Find Output File
        stem = pathlib.Path(audio_path).stem
        
        candidates = [
            output_dir / f"{stem}.mid",
            output_dir / f"{stem}.midi",
            output_dir / f"{stem}.txt", 
            output_dir / f"{stem}.csv", 
            output_dir / f"{stem}_vocal.mid",
            output_dir / f"{stem}.wav" 
        ]
        
        for cand in candidates:
             if cand.exists():
                  return str(cand)
        
        logging.error(f"Could not find output file in {output_dir}")
        print(f"Files in output dir: {list(output_dir.glob('*'))}")
        return None

    except Exception as e:
        stop_event.set()
        logging.exception(f"Error running Omnizart {mode} transcription")
        return None
