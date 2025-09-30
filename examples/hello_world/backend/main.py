from backend.app import App
from backend.simpledb import exec as db_exec, query_all, query_one
from backend.auth import hash_password, check_password, create_token, verify_token, parse_bearer
from backend.config import HOST, PORT, CORS_ALLOW_ORIGIN, RATE_LIMIT_PER_MIN

app = App()

# ---------- DB bootstrap ----------
db_exec("""
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  password_hash BLOB NOT NULL
)
""")

db_exec("""
CREATE TABLE IF NOT EXISTS todos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  done INTEGER NOT NULL DEFAULT 0,
  user_id INTEGER,
  FOREIGN KEY (user_id) REFERENCES users(id)
)
""")

# Seed demo user if not exists
if not query_one("SELECT id FROM users WHERE email=?", ("demo@user.com",)):
    db_exec("INSERT INTO users(email, password_hash) VALUES (?,?)",
            ("demo@user.com", hash_password("demo123")))

# ---------- health (public) ----------
@app.route("/health", methods=["GET"])
def health(request=None):
    return {"status": "ok"}

# ---------- auth helper (middleware wrapper) ----------
def auth_required(next_handler):
    def wrapped(request):
        token = parse_bearer(request["headers"].get("Authorization"))
        claims = verify_token(token) if token else None
        if not claims:
            return ({"error": "unauthorized"}, 401)
        request["user"] = {"id": claims["sub"], "email": claims["email"]}
        return next_handler(request)
    return wrapped

# ---------- public routes ----------
@app.route("/hello", methods=["GET"])
def hello(request=None):
    return {"message": "Hello from PyReactX on macOS 🎉 (SQLite + JWT + .env + rate-limit)"}

# POST /auth/register {email,password}
@app.route("/auth/register", methods=["POST"])
def register(request):
    data = request["json"]
    if not data:
        return ({"error": "invalid JSON body"}, 400)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return ({"error": "email and password required"}, 400)
    if query_one("SELECT id FROM users WHERE email=?", (email,)):
        return ({"error": "email already in use"}, 409)
    db_exec("INSERT INTO users(email, password_hash) VALUES (?,?)", (email, hash_password(password)))
    user = query_one("SELECT id, email FROM users WHERE email=?", (email,))
    token = create_token(user["id"], user["email"])
    return {"user": user, "token": token}

# POST /auth/login {email,password}
@app.route("/auth/login", methods=["POST"])
def login(request):
    data = request["json"]
    if not data:
        return ({"error": "invalid JSON body"}, 400)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = query_one("SELECT id, email, password_hash FROM users WHERE email=?", (email,))
    if not user or not check_password(password, user["password_hash"]):
        return ({"error": "invalid credentials"}, 401)
    token = create_token(user["id"], user["email"])
    return {"user": {"id": user["id"], "email": user["email"]}, "token": token}

# ---------- protected routes ----------
@app.route("/me", methods=["GET"])
def me(request):
    return {"user": request.get("user")}

# GET /todos?page=1&limit=10
@app.route("/todos", methods=["GET"])
def list_todos(request):
    user = request.get("user")
    if not user:
        return ({"error": "unauthorized"}, 401)

    # pagination parse + bounds
    try:
        page = int(request["query"].get("page", 1))
        limit = int(request["query"].get("limit", 10))
    except Exception:
        return ({"error": "bad pagination params"}, 400)
    page = max(page, 1)
    limit = max(min(limit, 50), 1)
    offset = (page - 1) * limit

    # Inline LIMIT/OFFSET (some sqlite builds dislike placeholders there)
    items_sql = (
        "SELECT id, title, done FROM todos "
        "WHERE user_id=? "
        f"ORDER BY id DESC LIMIT {limit} OFFSET {offset}"
    )
    items = query_all(items_sql, (user["id"],))
    for r in items:
        r["done"] = bool(r["done"])

    total_row = query_one("SELECT COUNT(*) AS c FROM todos WHERE user_id=?", (user["id"],))
    total = total_row["c"] if total_row else 0

    return {"items": items, "page": page, "limit": limit, "total": total}

# POST /todos {title}
@app.route("/todos", methods=["POST"])
def create_todo(request):
    user = request.get("user")
    if not user:
        return ({"error": "unauthorized"}, 401)

    data = request["json"]
    if not data:
        return ({"error": "invalid JSON body"}, 400)
    title = (data.get("title") or "").strip()
    if not title:
        return ({"error": "title is required"}, 400)

    db_exec("INSERT INTO todos(title, done, user_id) VALUES (?,?,?)", (title, 0, user["id"]))
    item = query_one("SELECT id, title, done FROM todos WHERE user_id=? ORDER BY id DESC LIMIT 1", (user["id"],))
    item["done"] = bool(item["done"])
    return (item, 201)

# PATCH /todos/:id/toggle
@app.route("/todos/:id/toggle", methods=["PATCH"])
def toggle_todo(request):
    user = request.get("user")
    if not user:
        return ({"error": "unauthorized"}, 401)

    tid = request["params"]["id"]
    row = query_one("SELECT done FROM todos WHERE id=? AND user_id=?", (tid, user["id"]))
    if not row:
        return ({"error": "not found"}, 404)
    new_val = 0 if row["done"] else 1
    db_exec("UPDATE todos SET done=? WHERE id=? AND user_id=?", (new_val, tid, user["id"]))
    item = query_one("SELECT id, title, done FROM todos WHERE id=? AND user_id=?", (tid, user["id"]))
    item["done"] = bool(item["done"])
    return item

# DELETE /todos/:id
@app.route("/todos/:id", methods=["DELETE"])
def delete_todo(request):
    user = request.get("user")
    if not user:
        return ({"error": "unauthorized"}, 401)

    tid = request["params"]["id"]
    if not query_one("SELECT id FROM todos WHERE id=? AND user_id=?", (tid, user["id"])):
        return ({"error": "not found"}, 404)
    db_exec("DELETE FROM todos WHERE id=? AND user_id=?", (tid, user["id"]))
    return ({"status": "deleted"}, 200)

# ---------- OpenAPI spec ----------
@app.route("/openapi.json", methods=["GET"])
def openapi_json(request=None):
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "PyReactX API",
            "version": "1.0.0",
            "description": "Minimal auth + todos API for the PyReactX demo."
        },
        "servers": [{"url": "http://127.0.0.1:5000"}],
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health",
                    "responses": {"200": {"description": "OK", "content": {
                        "application/json": {"schema": {"type": "object","properties": {"status":{"type":"string"}}}}
                    }}}
                }
            },
            "/hello": {
                "get": { "summary": "Hello", "responses": {"200": {"description": "OK"}} }
            },
            "/auth/register": {
                "post": {
                    "summary": "Register",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {
                            "type":"object","required":["email","password"],
                            "properties":{"email":{"type":"string"},"password":{"type":"string"}}
                        }}}
                    },
                    "responses": {
                        "200": {"description": "Registered", "content":{"application/json":{"schema":{
                            "type":"object","properties":{
                                "user":{"$ref":"#/components/schemas/User"},
                                "token":{"type":"string"}
                            }
                        }}}},
                        "400": {"$ref":"#/components/responses/BadRequest"},
                        "409": {"$ref":"#/components/responses/Conflict"}
                    }
                }
            },
            "/auth/login": {
                "post": {
                    "summary": "Login",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {
                            "type":"object","required":["email","password"],
                            "properties":{"email":{"type":"string"},"password":{"type":"string"}}
                        }}}
                    },
                    "responses": {
                        "200": {"description":"Logged in","content":{"application/json":{"schema":{
                            "type":"object","properties":{
                                "user":{"$ref":"#/components/schemas/User"},
                                "token":{"type":"string"}
                            }
                        }}}},
                        "401": {"$ref":"#/components/responses/Unauthorized"}
                    }
                }
            },
            "/me": {
                "get": {
                    "summary": "Current user",
                    "security": [{"bearerAuth": []}],
                    "responses": {
                        "200": {"description": "OK"},
                        "401": {"$ref":"#/components/responses/Unauthorized"}
                    }
                }
            },
            "/todos": {
                "get": {
                    "summary": "List todos",
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {"name":"page","in":"query","schema":{"type":"integer","default":1}},
                        {"name":"limit","in":"query","schema":{"type":"integer","default":10}}
                    ],
                    "responses": {
                        "200": {"description":"OK","content":{"application/json":{"schema":{"$ref":"#/components/schemas/TodoList"}}}},
                        "401": {"$ref":"#/components/responses/Unauthorized"}
                    }
                },
                "post": {
                    "summary": "Create todo",
                    "security": [{"bearerAuth": []}],
                    "requestBody": {"required": True, "content":{"application/json":{"schema":{
                        "type":"object","required":["title"],"properties":{"title":{"type":"string"}}
                    }}}},
                    "responses": {
                        "201": {"description":"Created","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Todo"}}}},
                        "400": {"$ref":"#/components/responses/BadRequest"},
                        "401": {"$ref":"#/components/responses/Unauthorized"}
                    }
                }
            },
            "/todos/{id}/toggle": {
                "patch": {
                    "summary":"Toggle done",
                    "security": [{"bearerAuth": []}],
                    "parameters":[{"name":"id","in":"path","required":True,"schema":{"type":"integer"}}],
                    "responses":{
                        "200":{"description":"OK","content":{"application/json":{"schema":{"$ref":"#/components/schemas/Todo"}}}},
                        "401":{"$ref":"#/components/responses/Unauthorized"},
                        "404":{"$ref":"#/components/responses/NotFound"}
                    }
                }
            },
            "/todos/{id}": {
                "delete": {
                    "summary":"Delete todo",
                    "security":[{"bearerAuth":[]}],
                    "parameters":[{"name":"id","in":"path","required":True,"schema":{"type":"integer"}}],
                    "responses":{
                        "200":{"description":"Deleted"},
                        "401":{"$ref":"#/components/responses/Unauthorized"},
                        "404":{"$ref":"#/components/responses/NotFound"}
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type":"http","scheme":"bearer","bearerFormat":"JWT"}
            },
            "schemas": {
                "User": {"type":"object","properties":{"id":{"type":"integer"},"email":{"type":"string"}}},
                "Todo": {"type":"object","properties":{"id":{"type":"integer"},"title":{"type":"string"},"done":{"type":"boolean"}}},
                "TodoList": {"type":"object","properties":{
                    "items":{"type":"array","items":{"$ref":"#/components/schemas/Todo"}},
                    "page":{"type":"integer"},"limit":{"type":"integer"},"total":{"type":"integer"}
                }}
            },
            "responses": {
                "BadRequest": {"description":"Bad request","content":{"application/json":{"schema":{"type":"object","properties":{"error":{"type":"string"}}}}}},
                "Unauthorized": {"description":"Unauthorized","content":{"application/json":{"schema":{"type":"object","properties":{"error":{"type":"string"}}}}}},
                "NotFound": {"description":"Not found","content":{"application/json":{"schema":{"type":"object","properties":{"error":{"type":"string"}}}}}},
                "Conflict": {"description":"Conflict","content":{"application/json":{"schema":{"type":"object","properties":{"error":{"type":"string"}}}}}}
            }
        }
    }
    return spec


# ---------- simple global rate-limit middleware ----------
import time
from collections import defaultdict, deque
from backend.config import RATE_LIMIT_PER_MIN

_requests = defaultdict(deque)  # ip -> deque[timestamps]

def rate_limit(next_handler):
    def wrapped(request):
        ip = request.get("ip", "local")
        now = time.time()
        window = 60.0
        q = _requests[ip]

        # evict old timestamps
        while q and now - q[0] > window:
            q.popleft()

        if len(q) >= RATE_LIMIT_PER_MIN:
            return ({"error": "rate limit exceeded", "limit_per_min": RATE_LIMIT_PER_MIN}, 429)

        q.append(now)
        return next_handler(request)
    return wrapped

# apply logging & rate limit
def logger(next_handler):
    def wrapped(request):
        print(f"[LOG] {request['method']} {request['path']}")
        return next_handler(request)
    return wrapped

app.use(rate_limit)
app.use(logger)

# ---------- wrap protected endpoints with auth middleware ----------
app.routes["/me"]["GET"]                      = auth_required(app.routes["/me"]["GET"])
app.routes["/todos"]["GET"]                   = auth_required(app.routes["/todos"]["GET"])
app.routes["/todos"]["POST"]                  = auth_required(app.routes["/todos"]["POST"])
app.routes["/todos/:id/toggle"]["PATCH"]      = auth_required(app.routes["/todos/:id/toggle"]["PATCH"])
app.routes["/todos/:id"]["DELETE"]            = auth_required(app.routes["/todos/:id"]["DELETE"])

# ---------- start ----------
if __name__ == "__main__":
    from backend.config import HOST, PORT, CORS_ALLOW_ORIGIN
    app.run(host=HOST, port=PORT, allow_origin=CORS_ALLOW_ORIGIN)
