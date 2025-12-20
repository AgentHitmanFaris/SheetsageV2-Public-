import os
import glob

def patch_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replacements for Python 3.10+ compatibility
        replacements = [
            ("from collections import MutableSequence", "from collections.abc import MutableSequence"),
            ("from collections import Iterable", "from collections.abc import Iterable"),
            ("from collections import Mapping", "from collections.abc import Mapping"),
            ("from collections import Sequence", "from collections.abc import Sequence"),
            ("np.float(", "float("),
            ("np.float)", "float)"),
            ("np.float,", "float,"),
            ("np.float ", "float "),
            ("np.int(", "int("),
            ("np.int)", "int)"),
            ("np.int,", "int,"),
            ("np.int ", "int "),
            # Be careful with np.float32/64 which are valid. "np.float" is the issue.
            # Using specific replacements above to avoid breaking np.float32
        ]
        
        # Additional safer regex-like replacement logic might be needed but simple replace works for 99% cases
        # Let's do a more robust one for np.float vs np.float32
        
        modified = False
        current_content = content
        for old, new in replacements:
            if old in current_content:
                current_content = current_content.replace(old, new)

        # Handle simple "np.float" assignment or return
        # A simple string replace of "np.float" -> "float" is dangerous if we have "np.floating".
        # But "np.float" is usually used as a type or caster.
        
        # Let's try to be specific for Madmom which uses "dtype=np.float" a lot.
        current_content = current_content.replace("dtype=np.float ", "dtype=float ")
        current_content = current_content.replace("dtype=np.float,", "dtype=float,")
        current_content = current_content.replace("dtype=np.float)", "dtype=float)")
        
        if current_content != original_content:
            modified = True
            content = current_content
            print(f"Patched numpy/collections in {filepath}")
        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
                
    except Exception as e:
        print(f"Failed to patch {filepath}: {e}")

def main():
    package_dir = os.path.join(os.getcwd(), "python_embeded", "Lib", "site-packages", "madmom")
    if not os.path.exists(package_dir):
        print(f"Madmom directory not found at {package_dir}")
        return

    print(f"Scanning {package_dir}...")
    for root, dirs, files in os.walk(package_dir):
        for file in files:
            if file.endswith(".py"):
                patch_file(os.path.join(root, file))
    
    # Also patch BeatNet if needed (though it seems fine/updated)
    beatnet_dir = os.path.join(os.getcwd(), "python_embeded", "Lib", "site-packages", "BeatNet")
    if os.path.exists(beatnet_dir):
         print(f"Scanning {beatnet_dir}...")
         for root, dirs, files in os.walk(beatnet_dir):
            for file in files:
                if file.endswith(".py"):
                    patch_file(os.path.join(root, file))

if __name__ == "__main__":
    main()
