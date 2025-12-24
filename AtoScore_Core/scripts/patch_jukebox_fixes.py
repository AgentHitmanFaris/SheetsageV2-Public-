
import os
import sys

# Define path to the site-packages
site_packages = r"D:\Document\atoscore\python_embeded\lib\site-packages"
jukebox_pkg = os.path.join(site_packages, "jukebox")

if not os.path.exists(jukebox_pkg):
    print("Jukebox package not found at:", jukebox_pkg)
    sys.exit(1)

print(f"Found Jukebox at: {jukebox_pkg}")

# --- Patch 1: remote_utils.py (Fix: Replace buggy wget with urllib) ---
remote_utils_path = os.path.join(jukebox_pkg, "utils", "remote_utils.py")
print(f"Patching {remote_utils_path}...")

new_remote_utils_code = """
import os
import urllib.request
from tqdm import tqdm

def download(remote_path, local_path):
    if os.path.exists(local_path):
        print(f"File {local_path} already exists. Skipping download.")
        return

    print(f"Downloading {remote_path} to {local_path}...")
    dir_path = os.path.dirname(local_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    try:
        with tqdm(unit='B', unit_scale=True, miniters=1, desc=os.path.basename(local_path)) as t:
            def reporthook(blocknum, blocksize, totalsize):
                t.total = totalsize
                t.update(blocknum * blocksize - t.n)
            
            urllib.request.urlretrieve(remote_path, local_path, reporthook=reporthook)
    except Exception as e:
        print(f"Download failed: {e}")
        # Clean up partial file
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except:
                pass
        raise e
"""

try:
    with open(remote_utils_path, "w", encoding="utf-8") as f:
        f.write(new_remote_utils_code)
    print("Successfully patched remote_utils.py")
except Exception as e:
    print(f"Failed to patch remote_utils.py: {e}")


# --- Patch 2: dist_adapter.py (Fix: Prevent barrier crash on single node) ---
dist_adapter_path = os.path.join(jukebox_pkg, "utils", "dist_adapter.py")
print(f"Patching {dist_adapter_path}...")

try:
    with open(dist_adapter_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # We want to make sure barrier() is safe to call even if dist is not initialized
    original_barrier = "return dist.barrier()"
    patched_barrier = "if dist.is_available() and dist.is_initialized(): return dist.barrier()"
    
    original_rank = "return dist.get_rank()"
    patched_rank = "return dist.get_rank() if (dist.is_available() and dist.is_initialized()) else 0"
    
    original_size = "return dist.get_world_size()"
    patched_size = "return dist.get_world_size() if (dist.is_available() and dist.is_initialized()) else 1"
    
    mod_count = 0
    if original_barrier in content:
        content = content.replace(original_barrier, patched_barrier)
        mod_count += 1
    
    if original_rank in content:
        content = content.replace(original_rank, patched_rank)
        mod_count += 1
        
    if original_size in content:
        content = content.replace(original_size, patched_size)
        mod_count += 1
        
    if mod_count > 0:
        with open(dist_adapter_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Successfully patched dist_adapter.py ({mod_count} replacements)")
    else:
        print("dist_adapter.py seems already patched or structure mismatch.")

except Exception as e:
    print(f"Failed to patch dist_adapter.py: {e}")


# --- Patch 3: Remove .cuda() calls (Fix: Allow CPU execution) ---
print("Scanning for .cuda() calls to remove (for CPU compatibility)...")
count_cuda = 0
for root, dirs, files in os.walk(jukebox_pkg):
    for file in files:
        if file.endswith(".py"):
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    c = f.read()
                
                if ".cuda()" in c:
                    c = c.replace(".cuda()", "")
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(c)
                    count_cuda += 1
                    print(f"Removed .cuda() from {file}")
            except Exception as e:
                print(f"Failed to process {file_path}: {e}")

print(f"Patching Complete. Modified {count_cuda} files for CPU compatibility.")

