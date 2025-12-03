import os

# Files to delete
files_to_delete = [
    "cleanup_legacy.py",
    "delete_cleanup_script.py"
]

for file in files_to_delete:
    if os.path.exists(file):
        os.remove(file)
        print(f"✅ Deleted: {file}")
    else:
        print(f"⚠️ Not found: {file}")

print("\n✨ Cleanup complete!")

# Delete this script itself
if os.path.exists("final_cleanup.py"):
    os.remove("final_cleanup.py")
    print("✅ Self-deleted: final_cleanup.py")
