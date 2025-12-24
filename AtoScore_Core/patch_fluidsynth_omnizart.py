import os

file_path = r"d:\Document\sheetsage\SheetSage_Core\omnizart_env\lib\site-packages\fluidsynth.py"

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    exit(1)

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
patched = False
for line in lines:
    if "os.add_dll_directory('C:\\\\tools\\\\fluidsynth\\\\bin')" in line or \
       'os.add_dll_directory("C:\\\\tools\\\\fluidsynth\\\\bin")' in line or \
       "os.add_dll_directory('C:/tools/fluidsynth/bin')" in line or \
       "os.add_dll_directory" in line and "fluidsynth" in line and "bin" in line:
        
        # Check if already patched to avoid recursion if run multiple times
        if "try:" in line or "except" in line: 
             new_lines.append(line)
             continue
             
        print(f"Patching line: {line.strip()}")
        # Wrap in try/except or just comment out if it's strictly optional
        # It seems this line was added by some installer?
        # Let's wrap it.
        new_lines.append(f"try: {line.strip()}\n")
        new_lines.append("except OSError: pass\n")
        patched = True
    else:
        new_lines.append(line)

if patched:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Successfully patched fluidsynth.py")
else:
    print("No patch needed or line not found.")
