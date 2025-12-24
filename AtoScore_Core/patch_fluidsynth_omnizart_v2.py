import os

file_path = r"d:\Document\atoscore\atoscore_Core\omnizart_env\lib\site-packages\fluidsynth.py"

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    exit(1)

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# The block usually looks like:
# if hasattr(os, 'add_dll_directory'):  # Python 3.8+ on Windows only
#     os.add_dll_directory(os.getcwd())
#     os.add_dll_directory('C:\\tools\\fluidsynth\\bin')
#     # Workaround bug in find_library, it doesn't recognize add_dll_directory
#     os.environ['PATH'] += ';C:\\tools\\fluidsynth\\bin'

# Or my previous patch might have mangled it to:
# try: os.add_dll_directory('C:\\tools\\fluidsynth\\bin')
# except OSError: pass
#     os.environ['PATH'] += ';C:\\tools\\fluidsynth\\bin'

# I will define replacement targets that match the mangled or original state
targets = [
    "try: os.add_dll_directory('C:\\\\tools\\\\fluidsynth\\\\bin')\nexcept OSError: pass\n    # Workaround bug in find_library, it doesn't recognize add_dll_directory\n    os.environ['PATH'] += ';C:\\\\tools\\\\fluidsynth\\\\bin'",
    "try: os.add_dll_directory('C:\\\\tools\\\\fluidsynth\\\\bin')\nexcept OSError: pass\n    os.environ['PATH'] += ';C:\\\\tools\\\\fluidsynth\\\\bin'"
]

# We just want to comment this whole C:\tools thing out or make it robust properly
# Note: os.environ['PATH'] += is outside the try/except in my bad patch?
# Let's just find the offending lines and comment them out.

lines = content.splitlines()
new_lines = []
skip_next = False

for i, line in enumerate(lines):
    if "os.add_dll_directory('C:\\\\tools\\\\fluidsynth\\\\bin')" in line or \
       'os.add_dll_directory("C:\\\\tools\\\\fluidsynth\\\\bin")' in line:
        
        # This is the line that crashes if dir not found.
        # We will wrap it safely properly this time.
        new_lines.append("    try:")
        new_lines.append("        os.add_dll_directory(r'C:\\tools\\fluidsynth\\bin')")
        new_lines.append("        os.environ['PATH'] += r';C:\\tools\\fluidsynth\\bin'")
        new_lines.append("    except OSError:")
        new_lines.append("        pass")
        
        # Now we need to skip the next lines if they were the old hardcoded ones
        # Use a lookahead to see if next lines are the 'PATH' addition and skip them
        # This is tricky without parsing.
        
        # Strategy: Just comment out the specific crash lines in place if they appear
        continue
        
    if "os.environ['PATH'] += ';C:\\\\tools\\\\fluidsynth\\\\bin'" in line:
        # We handled this above inside the try block (conceptually)
        # So we skip this line here
        continue
        
    # Fix my previous bad patch lines if they exist
    if "try: os.add_dll_directory" in line and "bin" in line:
         # Found my bad patch line
         new_lines.append("    try:")
         new_lines.append("        os.add_dll_directory(r'C:\\tools\\fluidsynth\\bin')")
         new_lines.append("    except OSError: pass")
         continue
         
    new_lines.append(line)

# Re-read and check if valid python?
# Actually, the simplest way is to just overwrite the file with a known good block for that section.

# Let's try to locate the block start "if hasattr(os, 'add_dll_directory'):"
# And then replace the next few lines.

final_content = []
lines = content.splitlines()
i = 0
patched = False
while i < len(lines):
    line = lines[i]
    if "if hasattr(os, 'add_dll_directory'):" in line:
        final_content.append(line)
        # consume lines until we find something that looks like the end of this block or next function
        # The block usually contains os.getcwd() and the hardcoded path.
        
        # Add safe block
        final_content.append("    try:")
        final_content.append("        os.add_dll_directory(os.getcwd())")
        final_content.append("    except OSError: pass")
        
        final_content.append("    try:")
        final_content.append("        os.add_dll_directory(r'C:\\tools\\fluidsynth\\bin')")
        final_content.append("        os.environ['PATH'] += r';C:\\tools\\fluidsynth\\bin'")
        final_content.append("    except OSError:")
        final_content.append("        pass")
        
        # Skip original lines to avoid duplication
        i += 1
        while i < len(lines):
             curr = lines[i]
             if "os.add_dll_directory" in curr or "fluidsynth" in curr and "bin" in curr:
                 i += 1
             elif curr.strip().startswith("# Workaround"):
                 i += 1
             elif curr.strip() == "try: os.add_dll_directory('C:\\\\tools\\\\fluidsynth\\\\bin')": # My bad patch
                 i += 1
             elif curr.strip() == "except OSError: pass":
                 i += 1
             else:
                 break
        patched = True
        continue
    
    final_content.append(line)
    i += 1

if patched:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_content))
    print("Repatched fluidsynth.py")
else:
    print("Could not find patch target block.")


