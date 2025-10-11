# PyReactX — Minimal Full-Stack Template (Python + React) with Auth, DB, CI & Cloud Deploy

![License](https://img.shields.io/badge/license-MIT-blue)

**PyReactX** is a tiny, readable full-stack starter that takes beginners from “hello world” to a **production-like** app: React SPA, Python API, JWT auth, SQLite, OpenAPI docs, CI, and cloud deploy (Render + Netlify).

> Demo credentials for local runs: `demo@user.com` / `demo123`

---

## Why this project is useful

Most tutorials skip real-world parts (CORS, tokens, envs, CI, deploy). **PyReactX** keeps the codebase small so you can read it end-to-end, and still includes:

- ✅ **JWT auth** (register/login) with bcrypt hashing  
- ✅ **SQLite** persistence (no external DB needed for dev)  
- ✅ Correct **CORS** for local + cloud  
- ✅ Simple **rate-limit** middleware  
- ✅ **OpenAPI** schema you can import in Swagger/Postman  
- ✅ **CI (GitHub Actions)** with tests + formatting  
- ✅ **Cloud deploy**: API on Render (Docker) + SPA on Netlify (instructions included)

Perfect as a portfolio piece: small enough to understand, realistic enough to ship.

---

## Features

- Login/Register → gets JWT, stored in `localStorage`, auto-sent as `Authorization: Bearer …`
- Todo CRUD (user-scoped) with pagination
- `/health` endpoint, `/openapi.json` spec, optional Swagger page (`myapp/docs.html`)
- Global rate-limit (requests/min/IP)
- Runtime API config so **same build works locally and in prod**

---

## Architecture

```
React SPA (Netlify)  <--->  PyReactX API (Render)
  | fetch(API_BASE)               | JWT issue/verify, CORS, rate-limit
  |                               v
  |---------------------------> SQLite (file on server)
```

- Frontend reads `API_BASE` from a tiny **runtime-config.js** generated at build time.
- Backend is a ~200-line micro-framework (routing, JSON, CORS, middleware).

---

## Project Structure

```
pyreactx/
├─ backend/
│  ├─ app.py           # tiny HTTP framework (routing, CORS, JSON, middleware)
│  ├─ auth.py          # JWT + bcrypt helpers
│  ├─ config.py        # HOST/PORT/CORS/JWT_SECRET/RATE_LIMIT from env
│  └─ simpledb.py      # SQLite helpers
├─ examples/
│  └─ hello_world/
│     └─ backend/main.py   # API app: routes, middleware, OpenAPI
├─ myapp/                  # React SPA (Parcel)
│  ├─ index.html
│  ├─ index.js
│  ├─ styles.css
│  └─ runtime-config.js    # overwritten in Netlify build to set window.API_BASE
├─ .github/workflows/ci.yml
├─ Dockerfile              # backend (Render)
├─ netlify.toml            # frontend (Netlify)
└─ README.md
```

---

## Quickstart (Local)

### 1) Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install bcrypt PyJWT python-dotenv
python3 -m examples.hello_world.backend.main
# ✅ http://127.0.0.1:5000
```

Optional `.env` for local:
```env
HOST=127.0.0.1
PORT=5000
CORS_ALLOW_ORIGIN=*
JWT_SECRET=dev-only-change-me
RATE_LIMIT_PER_MIN=60
```

### 2) Frontend

```bash
cd myapp
npm install
npm start
# ✅ http://localhost:1234
```

> **Local dev calls local API** by default. In production the Netlify build sets `window.API_BASE` to your backend URL.

---

## Environment (Production)

**Render (backend)**  
Set in Render → *Service → Environment*:
- `CORS_ALLOW_ORIGIN` = `https://<your-site>.netlify.app`  *(no trailing slash)*
- `JWT_SECRET` = long random string
- `RATE_LIMIT_PER_MIN` = `60`

**Netlify (frontend)**  
Set in Netlify → *Site settings → Build & deploy → Environment variables*:
- `API_BASE` = `https://<your-render-service>.onrender.com`

**Netlify build** (from `netlify.toml`) writes `myapp/runtime-config.js`:
```toml
[build]
  base    = "myapp"
  command = "bash -lc 'echo Building with API_BASE=$API_BASE && printf "window.API_BASE=\"%s\";\n" "$API_BASE" > runtime-config.js && npm ci && npm run build'"
  publish = "dist"
```

---

## API (Quick Reference)

| Method | Path                     | Auth | Description                    |
|-------:|--------------------------|:----:|--------------------------------|
| GET    | `/health`                |  –   | Service status                 |
| GET    | `/hello`                 |  –   | Welcome message                |
| POST   | `/auth/register`         |  –   | Create user `{email,password}` |
| POST   | `/auth/login`            |  –   | Login, returns `{user, token}` |
| GET    | `/me`                    | JWT  | Current user                   |
| GET    | `/todos?page&limit`      | JWT  | Paginated todos                |
| POST   | `/todos`                 | JWT  | Create `{title}`               |
| PATCH  | `/todos/:id/toggle`      | JWT  | Toggle done                    |
| DELETE | `/todos/:id`             | JWT  | Delete todo                    |

OpenAPI: `/openapi.json`

---

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every push/PR:

- Install Python deps
- Format check (Black)
- Tests (Pytest – includes a placeholder test)

Add a badge (optional):
```md
![CI](https://github.com/<YOUR_USERNAME>/pyreactx/actions/workflows/ci.yml/badge.svg)
```

---

## Deployment

### Backend → Render (Docker)
1. Push repo to GitHub.
2. Render: **New → Web Service → Docker → select repo**.
3. Env vars: set `JWT_SECRET`, `CORS_ALLOW_ORIGIN`, `RATE_LIMIT_PER_MIN`.
4. Deploy. Verify:
   - `/health` responds `{"status":"ok"}`
   - `/openapi.json` loads

> Optional: Add a **Disk** mounted at `/app` so `pyreactx.db` persists redeploys.

### Frontend → Netlify
1. Netlify: **New site → Import from Git** → select repo.  
2. `netlify.toml` auto-configures build (`base=myapp`, `publish=dist`).  
3. Set env `API_BASE` to your Render URL.  
4. Deploy (use “Deploy project without cache” after env changes).  
5. Verify `/runtime-config.js` on the site contains your backend URL.

---

## Security Notes

- JWT stored in `localStorage` (simple demo). For higher security, move to HttpOnly cookies + CSRF.
- Rate limiting is in-memory; use Redis/CDN/WAF for real production scale.
- Rotate `JWT_SECRET` if compromised (invalidates existing tokens).

---

## Roadmap

- Refresh tokens + auto-renew
- Postgres option via SQLAlchemy
- Swagger UI page inside the SPA
- E2E tests (Playwright/Cypress)
- Role-based access

---

## Screenshots (replace with your own)

```
docs/screenshots/login.png
docs/screenshots/todos.png
```

---

## License

MIT © 2025 Vismay Parekh

---

### Troubleshooting

- **CORS blocked**  
  Ensure backend `CORS_ALLOW_ORIGIN` equals your exact frontend origin (no trailing slash).

- **Frontend still calls 127.0.0.1 in prod**  
  Check:
  1. Netlify build log prints `Building with API_BASE=...`  
  2. `/runtime-config.js` on the site contains your backend URL  
  3. In `index.html`, `<script src="./runtime-config.js"></script>` is **before** `<script type="module" src="./index.js"></script>`
