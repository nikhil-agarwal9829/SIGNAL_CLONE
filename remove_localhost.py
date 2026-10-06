import os
import re

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}` 
    # with `${process.env.NEXT_PUBLIC_API_URL}`
    content = content.replace(
        '${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}',
        '${process.env.NEXT_PUBLIC_API_URL}'
    )
    
    # Replace `(process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws")`
    # with `process.env.NEXT_PUBLIC_WS_URL!`
    content = content.replace(
        '(process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws")',
        'process.env.NEXT_PUBLIC_WS_URL!'
    )
    
    # Just in case, replace any raw `"http://localhost:8000` still left
    content = content.replace('"http://localhost:8000', '`${process.env.NEXT_PUBLIC_API_URL}')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for root, _, files in os.walk('frontend/src'):
    for file in files:
        if file.endswith('.tsx') or file.endswith('.ts'):
            path = os.path.join(root, file)
            fix_file(path)

print('Hardcoded URLs completely removed.')
