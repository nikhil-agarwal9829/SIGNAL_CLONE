import os

def replace_in_file(filepath, old, new):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    if old in content:
        content = content.replace(old, new)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

for root, _, files in os.walk('frontend/src/app'):
    for file in files:
        if file.endswith('.tsx'):
            path = os.path.join(root, file)
            # Replace double-quoted URL
            replace_in_file(path, '"http://localhost:8000', '`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}')
            # Replace template-literal URL
            replace_in_file(path, '`http://localhost:8000', '`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}')
            # Replace WebSocket URL
            replace_in_file(path, '"ws://localhost:8000/ws"', '(process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws")')

# Fix auth.py
auth_path = 'backend/routers/auth.py'
with open(auth_path, 'r', encoding='utf-8') as f:
    auth_content = f.read()

auth_content = auth_content.replace('secure=False', 'secure=True')
auth_content = auth_content.replace('samesite="lax"', 'samesite="none"')

with open(auth_path, 'w', encoding='utf-8') as f:
    f.write(auth_content)

print('Replacements complete.')
