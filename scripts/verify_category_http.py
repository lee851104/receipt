"""Fictional HTTP checks inside an isolated acceptance container; no datasets."""
import csv
import io
import json
import math
import sys
import time
import urllib.error
import urllib.request
import urllib.parse

expected = sys.argv[1]
base = "http://127.0.0.1:8000"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def request(path, data=None, headers=None):
    req = urllib.request.Request(base + path, data=data, headers=headers or {})
    try:
        with opener.open(req, timeout=30) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as response:
        return response.code, json.loads(response.read())

def post(path, payload, headers=None):
    return request(path, json.dumps(payload).encode(), {"Content-Type": "application/json", **(headers or {})})

deadline = time.monotonic() + 180
while True:
    try:
        status, health = request("/api/health")
        if status == 200:
            break
    except (OSError, ValueError):
        pass
    if time.monotonic() > deadline:
        raise RuntimeError("health_timeout")
    time.sleep(1)
assert health["models"]["category"] == expected
username = "r2docker" + str(time.time_ns())[-12:]
password = "fictional-acceptance-only"
assert post("/api/auth/register", {"username": username, "password": password})[0] == 201
status, login = request("/api/auth/login", urllib.parse.urlencode({"username": username, "password": password}).encode(), {"Content-Type": "application/x-www-form-urlencoded"})
assert status == 200
headers = {"Authorization": "Bearer " + login["access_token"]}
status, classified = post("/api/items/classify", {"name": "示範雞肉飯"}, headers)
assert status == (200 if expected == "bert" else 503)
if expected == "bert":
    probs = classified["probs"]
    assert len(probs) == 10 and all(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1 for x in probs)
    assert abs(sum(probs) - 1) < .001 and 0 <= classified["category"]["id"] < 10
else:
    assert classified["detail"] == "model_unavailable"
stream = io.StringIO()
writer = csv.writer(stream)
writer.writerow(["發票日期", "發票狀態", "發票號碼", "賣方名稱", "賣方地址", "消費明細_品名", "消費明細_數量", "消費明細_金額"])
for index, name in enumerate(["示範雞肉飯", "示範烏龍茶500ML", "示範貓砂6L"]):
    writer.writerow(["20260502", "開立已確認", "FICTIONAL-" + str(index), "虛構測試店", "虛構測試地址", name, 1, 100])
writer.writerow(["", "", "", "匯出摘要"])
boundary = "receiptrole2fictionalboundary"
body = ('--' + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="fictional.csv"\r\nContent-Type: text/csv\r\n\r\n\ufeff' + stream.getvalue() + '\r\n--' + boundary + '--\r\n').encode()
upload_status, upload = request("/api/invoices", body, {**headers, "Content-Type": "multipart/form-data; boundary=" + boundary})
assert upload_status == 202 and upload["rows"] == 3
deadline = time.monotonic() + 90
while True:
    status, job = request("/api/jobs/" + str(upload["job_id"]), headers=headers)
    assert status == 200
    if job["status"] in ("done", "failed"):
        break
    if time.monotonic() > deadline:
        raise RuntimeError("job_timeout")
    time.sleep(.2)
assert job["status"] == ("done" if expected == "bert" else "failed")
result = {"health": expected, "classify": 200 if expected == "bert" else 503, "upload": upload_status, "fictional_rows": 3, "job": job["status"]}
if expected == "bert":
    status, profile = request("/api/me/profile", headers=headers)
    assert status == 200 and profile["months"]
    result["profile"] = status
print(json.dumps(result))
