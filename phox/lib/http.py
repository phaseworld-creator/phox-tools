import json
import urllib.request
import urllib.parse
import urllib.error
import ssl
import http.client


class Response:

    def __init__(self, urllib_response, url):
        self._resp = urllib_response
        self.url = url
        self.status_code = urllib_response.status
        self.reason = urllib_response.reason
        self.headers = dict(urllib_response.headers)
        self.ok = 200 <= self.status_code < 400

    @property
    def content(self):
        return self._resp.read()

    @property
    def text(self):
        return self.content.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.text)

    @property
    def encoding(self):
        ct = self.headers.get("content-type", "")
        for part in ct.split(";"):
            part = part.strip()
            if part.startswith("charset="):
                return part.split("=", 1)[1]
        return "utf-8"


def request(method, url, headers=None, data=None, json_body=None,
            timeout=30, verify=True, allow_redirects=True):
    headers = dict(headers or {})

    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    elif isinstance(data, str):
        data = data.encode("utf-8")
        headers.setdefault("Content-Type", "text/plain")

    headers.setdefault("User-Agent", "PhoxTools/1.0")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    ctx = None
    if not verify:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    except urllib.error.HTTPError as e:
        resp = e

    return Response(resp, url)


def get(url, **kwargs):
    return request("GET", url, **kwargs)


def post(url, **kwargs):
    return request("POST", url, **kwargs)


def put(url, **kwargs):
    return request("PUT", url, **kwargs)


def patch(url, **kwargs):
    return request("PATCH", url, **kwargs)


def delete(url, **kwargs):
    return request("DELETE", url, **kwargs)
