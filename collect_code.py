import os

# الامتدادات المقبولة
EXTENSIONS = {'.py', '.html', '.css', '.js', '.json', '.sql', '.yaml', '.yml', '.ini', '.env', '.txt', '.md'}
# مجلدات يتم تجاهلها
IGNORE_DIRS = {'__pycache__', '.git', 'venv', 'env', 'node_modules', '.idea', '.vscode', 'alembic', 'migrations'}
# اسم الملف الناتج
OUTPUT_FILE = "full_project_code.txt"

def collect_files():
    # يبدأ البحث من نفس المكان الموجود فيه السكربت حالياً
    start_path = os.getcwd()
    
    found_count = 0
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        outfile.write(f"Project Code Collection\nRoot: {start_path}\n{'='*50}\n\n")
        
        for root, dirs, files in os.walk(start_path):
            # فلترة المجلدات
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                # نتجاهل السكربت نفسه والملف الناتج
                if file == os.path.basename(__file__) or file == OUTPUT_FILE:
                    continue
                    
                ext = os.path.splitext(file)[1]
                if ext in EXTENSIONS:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, start_path)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            content = infile.read()
                            # كتابة الفواصل واسم الملف
                            outfile.write(f"\n{'='*50}\n")
                            outfile.write(f"FILE: {rel_path}\n")
                            outfile.write(f"{'='*50}\n")
                            outfile.write(content)
                            outfile.write("\n")
                            
                            print(f"Added: {rel_path}") # طباعة للتأكد
                            found_count += 1
                    except Exception as e:
                        print(f"Error reading {rel_path}: {e}")

    print(f"\nDone! collected {found_count} files into '{OUTPUT_FILE}'")

if __name__ == "__main__":
    collect_files()
    input("Press Enter to exit...")