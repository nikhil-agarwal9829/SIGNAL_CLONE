import urllib.request
import os

AVATAR_DIR = "../frontend/public/avatars"
os.makedirs(AVATAR_DIR, exist_ok=True)

names = ["Felix", "Aneka", "Jasper", "Brian", "Caleb", "Avery", "Zoe", "Sam"]
for i, name in enumerate(names):
    url = f"https://api.dicebear.com/9.x/adventurer/svg?seed={name}"
    file_path = os.path.join(AVATAR_DIR, f"avatar{i+1}.svg")
    print(f"Downloading {name} to {file_path}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        with open(file_path, 'wb') as out_file:
            out_file.write(response.read())

print("Downloaded avatars successfully!")
