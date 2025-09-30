import json
import re
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer

class App:
    def __init__(self):
        # routes[pattern][method] = handler
        self.routes = {}
        self.middlewares = []

    def route(self, path, methods=["GET"]):
        def decorator(func):
            if path not in self.routes:
                self.routes[path] = {}
            for m in methods:
                self.routes[path][m.upper()] = func
            return func
        return decorator

    def use(self, middleware):
        """middleware(next_handler) -> wrapped_handler"""
        self.middlewares.append(middleware)

    def _apply_middlewares(self, handler):
        wrapped = handler
        for mw in reversed(self.middlewares):
            wrapped = mw(wrapped)
        return wrapped

    # support patterns like /todos/:id and /users/:id
    def _match_route(self, raw_path):
        parsed = urlparse(raw_path)
        path_only = parsed.path
        for pattern, methods in self.routes.items():
            # convert `:id` into a named regex group
            regex = re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", r"(?P<\1>[^/]+)", pattern)
            m = re.fullmatch(regex, path_only)
            if m:
                return methods, m.groupdict(), parsed
        return None, None, parsed

    def run(self, host="127.0.0.1", port=5000, allow_origin="*"):
        app = self

        class Handler(BaseHTTPRequestHandler):
            def _send_json(self, obj, status=200):
                data = json.dumps(obj).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", allow_origin)
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                self.send_header("Access-Control-Allow-Methods", "GET,POST,PATCH,DELETE,OPTIONS")
                self.end_headers()
                self.wfile.write(data)

            def _read_json(self):
                length = int(self.headers.get("Content-Length") or 0)
                if length == 0:
                    return None
                raw = self.rfile.read(length)
                try:
                    return json.loads(raw.decode())
                except Exception:
                    return None

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", allow_origin)
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                self.send_header("Access-Control-Allow-Methods", "GET,POST,PATCH,DELETE,OPTIONS")
                self.end_headers()

            def _dispatch(self, method):
                methods, path_params, parsed = app._match_route(self.path)
                if not methods:
                    self._send_json({"error": "Route not found"}, status=404)
                    return
                handler = methods.get(method)
                if not handler:
                    self._send_json({"error": f"Method {method} not allowed"}, status=405)
                    return

                query = {k: (v[0] if len(v)==1 else v) for k, v in parse_qs(parsed.query).items()}
                request = {
                    "method": method,
                    "path": parsed.path,
                    "headers": dict(self.headers.items()),
                    "query": query,
                    "params": path_params or {},
                    "json": self._read_json() if method in {"POST","PATCH","DELETE"} else None,
                    "ip": self.client_address[0],   # ← for rate-limiting
                }

                wrapped = app._apply_middlewares(handler)
                try:
                    result = wrapped(request)
                except Exception as e:
                    import traceback
                    print("=== SERVER ERROR ===")
                    print(traceback.format_exc())
                    self._send_json({"error": "Internal Server Error", "detail": str(e)}, status=500)
                    return

                if isinstance(result, tuple) and len(result) == 2:
                    body, status = result
                else:
                    body, status = result, 200
                self._send_json(body, status=status)

            def do_GET(self):     self._dispatch("GET")
            def do_POST(self):    self._dispatch("POST")
            def do_PATCH(self):   self._dispatch("PATCH")
            def do_DELETE(self):  self._dispatch("DELETE")

        print(f"✅ Server running at http://{host}:{port}")
        server = HTTPServer((host, port), Handler)
        server.serve_forever()
