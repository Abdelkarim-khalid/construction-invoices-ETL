import os
import shutil

# Create backup directory
backup_dir = "legacy_backup"
if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)
    print(f"Created directory: {backup_dir}")

# Files to move and their new names
files_to_move = {
    "main.py": "main_old.py",
    "models.py": "models_old.py",
    "schemas.py": "schemas_old.py",
    "database.py": "database_old.py",
    "frontend.py": "frontend_old.py",
    "services/invoice_processor.py": "invoice_processor_old.py"
}

for old_path, new_name in files_to_move.items():
    if os.path.exists(old_path):
        new_path = os.path.join(backup_dir, new_name)
        try:
            shutil.move(old_path, new_path)
            print(f"✅ Moved: {old_path} -> {new_path}")
        except Exception as e:
            print(f"❌ Error moving {old_path}: {e}")
    else:
        print(f"⚠️ File not found (already moved?): {old_path}")

print("\nCleanup complete!")
