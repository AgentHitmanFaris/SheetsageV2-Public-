import sys
import os
sys.path.append(os.getcwd())
import logging
from atoscore.modules.omnizart_transcription import run_omnizart

logging.basicConfig(level=logging.INFO)

input_file = r"d:\Document\atoscore\atoscore_Core\temp\safe_inputs\input_570bf76e.mp3"
output_dir = r"d:\Document\atoscore\atoscore_Core\temp\omnizart_debug"

# Ensure output dir exists
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

print(f"Testing Omnizart on {input_file}")
result = run_omnizart(input_file, output_dir, mode="drum")
if result:
    print(f"Success: {result}")
else:
    print("Failure")

