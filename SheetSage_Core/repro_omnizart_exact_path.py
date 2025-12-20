import os
import sys
sys.path.append(os.getcwd())
import logging
from sheetsage.modules.omnizart_transcription import run_omnizart

logging.basicConfig(level=logging.WARN)

# Exact path from user log
input_path = r"D:\Document\sheetsage\SheetSage_Core\temp\gradio\c1691270da6687787a71d98b1743e8c0afb3615e30b2900dd194989ae4872b04\Aisha Retno - Tak Adil Official Music Video fMiH9F7O9eM.mp3"
output_dir = r"D:\Document\sheetsage\SheetSage_Core\temp\debug_exact_path"

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

if not os.path.exists(input_path):
    print(f"File not found: {input_path}")
    # Try to find it in temp/gradio just in case folder is right
    sys.exit(0)

print(f"Testing Omnizart on exact path: {input_path}")
result = run_omnizart(input_path, output_dir, mode="drum")

if result:
    print(f"Success: {result}")
    size = os.path.getsize(result)
    print(f"Output size: {size} bytes")
    if size < 100:
        print("FAILURE: Output is empty.")
    else:
        print("SUCCESS: Output has content.")
else:
    print("Failure: No output.")
