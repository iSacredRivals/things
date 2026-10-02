#!/usr/bin/env python3
"""Download a gofile.io share folder to /home/z/my-project/downloads_cdn/."""
import json, os, re, sys, urllib.request

SHARE = sys.argv[1] if len(sys.argv) > 1 else "wGznpzDS"
OUT = "/home/z/my-project/downloads_cdn"
os.makedirs(OUT, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

def http(url, data=None, headers=None, method=None):
    h = {"User-Agent": UA}
    if headers: h.update(headers)
    if isinstance(data, dict):
        data = json.dumps(data).encode()
        h.setdefault("Content-Type", "application/json")
    elif isinstance(data, str):
        data = data.encode()
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

# 1) website token from the site JS bundle
js = ""
for candidate in ("https://gofile.io/dist/js/all.js", "https://gofile.io/dist/js/config.js"):
    try:
        js = http(candidate).decode("utf-8", "replace")
        m = re.search(r'websiteToken\s*[:=]\s*["\']([A-Za-z0-9]+)["\']', js)
        if m:
            break
    except Exception as e:
        print(f"[!] {candidate}: {e}", file=sys.stderr)
m = re.search(r'websiteToken\s*[:=]\s*["\']([A-Za-z0-9]+)["\']', js or "")
WT = m.group(1) if m else None
print(f"[*] website token: {WT}")

# 2) guest account
acc = json.loads(http("https://api.gofile.io/accounts", method="POST"))
TOKEN = acc["data"]["token"]
print(f"[*] guest token: {TOKEN[:12]}...")

# 3) content listing
url = f"https://api.gofile.io/contents/{SHARE}?wt={WT}"
meta = json.loads(http(url, headers={"Authorization": f"Bearer {TOKEN}"}))
if meta.get("status") != "ok":
    print("[!] listing failed:", json.dumps(meta)[:500]); sys.exit(1)
root = meta["data"]

def walk(node, path=""):
    for cid, ch in (node.get("children") or {}).items():
        name = ch.get("name", cid)
        if ch.get("type") == "folder":
            walk(ch, path + name + "/")
        else:
            link = ch.get("link") or ch.get("downloadUri")
            size = ch.get("size", 0)
            print(f"[*] file: {path}{name}  {size/1024:.1f} KB  {link}")
            dest = os.path.join(OUT, name)
            try:
                blob = http(link, headers={"Authorization": f"Bearer {TOKEN}"})
                with open(dest, "wb") as f: f.write(blob)
                print(f"[+] saved {dest} ({len(blob)/1024:.1f} KB)")
            except Exception as e:
                # retry without auth header
                try:
                    blob = http(link)
                    with open(dest, "wb") as f: f.write(blob)
                    print(f"[+] saved (noauth) {dest} ({len(blob)/1024:.1f} KB)")
                except Exception as e2:
                    print(f"[!] download failed {name}: {e2}", file=sys.stderr)

walk(root)
