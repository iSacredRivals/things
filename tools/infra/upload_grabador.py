#!/usr/bin/env python3
"""Sube el grabador a hosting público y devuelve links de descarga.

Prueba por archivo: catbox (link directo) -> gofile (página de descarga).
Extra: pastefy con el texto del .luau (link copiable / loadstring).

Uso: python3 upload_grabador.py <archivo> [<archivo>...]
"""
import json
import sys
import urllib.request
import uuid

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}


def post_multipart(url, fields, files, timeout=60):
    boundary = "----" + uuid.uuid4().hex
    parts = []
    for name, val in fields:
        parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
                      % (boundary, name, val)).encode())
    for name, fname, payload, ctype in files:
        parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; "
                      "filename=\"%s\"\r\nContent-Type: %s\r\n\r\n"
                      % (boundary, name, fname, ctype)).encode())
        parts.append(payload)
        parts.append(b"\r\n")
    parts.append(("--%s--\r\n" % boundary).encode())
    req = urllib.request.Request(
        url, data=b"".join(parts), method="POST",
        headers={"Content-Type": "multipart/form-data; boundary=" + boundary, **UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def get_json(url, data=None, method=None, headers=None, timeout=30):
    req = urllib.request.Request(url, data=data, method=method, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def upload_catbox(path):
    payload = open(path, "rb").read()
    out = post_multipart("https://catbox.moe/user/api.php",
                         [("reqtype", "fileupload")],
                         [("fileToUpload", path.split("/")[-1], payload, "application/octet-stream")])
    if out.strip().startswith("http"):
        return out.strip()
    raise RuntimeError("respuesta inesperada: %s" % out[:120])


def upload_gofile(path):
    acc = get_json("https://api.gofile.io/accounts", data=b"", method="POST")
    token = acc["data"]["token"]
    root = acc["data"]["rootFolderId"]
    srv = get_json("https://api.gofile.io/servers")["data"]["servers"][0]["name"]
    payload = open(path, "rb").read()
    out = post_multipart("https://%s.gofile.io/contents/uploadfile" % srv,
                         [("token", token), ("folderId", root)],
                         [("file", path.split("/")[-1], payload, "application/octet-stream")])
    j = json.loads(out)
    if j.get("status") == "ok":
        return j["data"]["downloadPage"]
    raise RuntimeError("status %s" % j.get("status"))


def upload_pixeldrain(path):
    payload = open(path, "rb").read()
    req = urllib.request.Request("https://pixeldrain.com/api/file/", data=payload,
                                 method="PUT", headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        j = json.loads(r.read().decode())
    if j.get("id"):
        return ("https://pixeldrain.com/u/%s (directo: "
                "https://pixeldrain.com/api/file/%s?download)" % (j["id"], j["id"]))
    raise RuntimeError(str(j)[:120])


def upload_filebin(path):
    binid = uuid.uuid4().hex[:12]
    url = "https://filebin.net/%s/%s" % (binid, path.split("/")[-1])
    req = urllib.request.Request(url, data=open(path, "rb").read(), method="POST",
                                 headers={**UA, "Accept": "application/json",
                                          "Content-Type": "application/octet-stream"})
    with urllib.request.urlopen(req, timeout=60) as r:
        j = json.loads(r.read().decode())
    return "https://filebin.net/%s/%s" % (binid, path.split("/")[-1])


def pastefy_text(path, title):
    txt = open(path, encoding="utf-8").read()
    req = urllib.request.Request(
        "https://pastefy.app/api/v2/paste",
        data=json.dumps({"title": title, "content": txt}).encode(),
        method="POST", headers={**UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read().decode())
    pid = j.get("id") or (j.get("paste") or {}).get("id")
    if pid:
        return "https://pastefy.app/%s (raw: https://pastefy.app/raw/%s)" % (pid, pid)
    raise RuntimeError("sin id: %s" % str(j)[:120])


def main():
    for p in sys.argv[1:]:
        name = p.split("/")[-1]
        link = None
        for host, fn in (("pixeldrain", upload_pixeldrain),
                         ("filebin", upload_filebin),
                         ("gofile", upload_gofile)):
            try:
                link = fn(p)
                print("[+] %s via %s: %s" % (name, host, link))
                break
            except Exception as e:
                print("[!] %s via %s fallo: %s" % (name, host, e), file=sys.stderr)
        if not link:
            print("[-] %s: no se pudo subir a ningun host" % name, file=sys.stderr)
    # pastefy del .luau (texto copiable + raw para loadstring)
    try:
        print("[+] pastefy: %s" % pastefy_text("/home/z/my-project/download/grabador_luraph.luau",
                                               "grabador_luraph.luau"))
    except Exception as e:
        print("[!] pastefy fallo: %s" % e, file=sys.stderr)


if __name__ == "__main__":
    main()
