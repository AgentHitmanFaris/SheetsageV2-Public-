
import os

file_path = r"D:\Document\atoscore\python_embeded\lib\site-packages\jukebox\utils\dist_adapter.py"

try:
    with open(file_path, 'r') as f:
        content = f.read()

    # Patch _get_rank
    if "return dist.get_rank()" in content:
        content = content.replace(
            "return dist.get_rank()",
            "if not dist.is_available() or not dist.is_initialized(): return 0\n    return dist.get_rank()"
        )
        print("Patched _get_rank")

    # Patch _get_world_size
    if "return dist.get_world_size()" in content:
        content = content.replace(
            "return dist.get_world_size()",
            "if not dist.is_available() or not dist.is_initialized(): return 1\n    return dist.get_world_size()"
        )
        print("Patched _get_world_size")

    with open(file_path, 'w') as f:
        f.write(content)
    print(f"Successfully patched {file_path}")

except Exception as e:
    print(f"Failed to patch {file_path}: {e}")

