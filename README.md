# PyReactX — Python + React microframework demo

A minimal end-to-end starter you can skim in minutes:

- Tiny Python HTTP microframework (routing, middleware, CORS, rate-limit)
- SQLite persistence
- JWT auth (register/login) with protected CRUD `/todos`
- React client (login + protected list + pagination)
- Config via `.env`, `/health` endpoint
- **OpenAPI** at `/openapi.json` + **Swagger UI** page in `/myapp/docs.html`

---

## Local Quickstart

### Backend 
```bash
pip3 install bcrypt PyJWT python-dotenv
python3 -m examples.hello_world.backend.main
# http://127.0.0.1:5000

---

### Frontend
cd myapp
npm install
npm run start
# http://localhost:1234

