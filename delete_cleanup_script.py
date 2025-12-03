import os
if os.path.exists("cleanup_legacy.py"):
    os.remove("cleanup_legacy.py")
    print("✅ Deleted cleanup_legacy.py")
else:
    print("⚠️ File already deleted")
