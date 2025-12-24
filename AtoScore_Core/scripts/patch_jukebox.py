
import os


import os
import glob

package_dir = r"D:\Document\sheetsage\python_embeded\lib\site-packages\jukebox"

print(f"Scanning {package_dir}...")

for root, dirs, files in os.walk(package_dir):
    for file in files:
        if file.endswith(".py"):
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if ".cuda()" in content:
                    print(f"Patching {file_path}")
                    new_content = content.replace(".cuda()", "")
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
            except Exception as e:
                print(f"Failed to process {file_path}: {e}")

