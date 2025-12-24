import os
import shutil
import sys
sys.path.append(os.getcwd())
from atoscore.modules.omnizart_transcription import run_omnizart

# Use the known good input file
src = r"d:\Document\atoscore\atoscore_Core\temp\safe_inputs\input_570bf76e.mp3"
# Create a destination with spaces
dest_dir = r"d:\Document\atoscore\atoscore_Core\temp\space_test"
if not os.path.exists(dest_dir):
    os.makedirs(dest_dir)

dest = os.path.join(dest_dir, "Aisha Retno - Tak Adil test.mp3")
if os.path.exists(src):
    shutil.copy(src, dest)
    print(f"Copied {src} to {dest}")
else:
    print(f"Source not found: {src}")
    exit(1)

output_dir = os.path.join(dest_dir, "output")

print(f"Testing Omnizart on '{dest}' (Has spaces)")
result = run_omnizart(dest, output_dir, mode="drum")

if result:
    print(f"Success: {result}")
    size = os.path.getsize(result)
    print(f"Output size: {size} bytes")
    if size < 100:
        print("FAILURE: Output is empty (likely just header).")
    else:
        print("SUCCESS: Output has content.")
else:
    print("Failure: No output returned.")

