import os

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # The broken string looks like:
    # `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/auth/profile",
    # Notice the trailing `",` which means the original string was closed with `"`.
    # Let's fix this globally.
    
    # Let's replace the broken structure with a proper constant approach or simply fix the template literals.
    import re
    # We want to replace: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/something"
    # with: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/something`
    
    # Regex to find these unclosed backticks that end in a double quote.
    # Pattern: \`\$\{process\.env\.NEXT_PUBLIC_API_URL \|\| "http://localhost:8000"\}([^"]*)"
    # Replace with: \`\$\{process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"\}\1\`
    
    content = re.sub(
        r'\`\$\{process\.env\.NEXT_PUBLIC_API_URL \|\| "http://localhost:8000"\}([^"]*)"',
        r'`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}\1`',
        content
    )
    
    # Also handle the one that was originally a backtick string
    # E.g. `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/conversations/${conv.id}/read`
    # That one might have ended up as `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api...`
    # Let's verify if there are any remaining double quotes where backticks belong.

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for root, _, files in os.walk('frontend/src/app'):
    for file in files:
        if file.endswith('.tsx'):
            path = os.path.join(root, file)
            fix_file(path)

print('Fixed.')
