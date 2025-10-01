// KEEP THIS AT THE TOP OF THE FILE
const API =
  (typeof window !== "undefined" && window.API_BASE) ||
  process.env.API_BASE ||
  "http://127.0.0.1:5000";

import React, { useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";





/* ---------- helpers ---------- */
async function api(path, { method = "GET", body, token } = {}) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.error || `HTTP ${res.status}`;
    throw Object.assign(new Error(msg), { status: res.status, data });
  }
  return data;
}

function useLocalStorage(key, initial) {
  const [v, setV] = useState(() => {
    const saved = localStorage.getItem(key);
    return saved ? JSON.parse(saved) : initial;
  });
  useEffect(() => localStorage.setItem(key, JSON.stringify(v)), [key, v]);
  return [v, setV];
}

/* ---------- Auth ---------- */
function Auth({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("demo@user.com");
  const [password, setPassword] = useState("demo123");
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const path = mode === "login" ? "/auth/login" : "/auth/register";
      const res = await api(path, { method: "POST", body: { email, password } });
      onAuth(res.token, res.user);
    } catch (err) {
      setError(err.message || "Auth failed");
    }
  };

  return (
    <div className="auth card">
      <div className="header">
        <h1>PyReactX</h1>
        <span className="badge">SQLite · JWT</span>
        <span className="spacer"></span>
      </div>

      <h2 className="section-title">{mode === "login" ? "Login" : "Create account"}</h2>
      <form onSubmit={submit} className="grid">
        <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
        <input className="input" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" type="password" />
        <button className="btn btn-primary">{mode === "login" ? "Login" : "Register"}</button>
      </form>

      {error && <p className="error" style={{ marginTop: 8 }}>{error}</p>}
      <p className="helper" style={{ marginTop: 8 }}>
        {mode === "login" ? (
          <>No account? <button className="btn" onClick={() => setMode("register")}>Register</button></>
        ) : (
          <>Have an account? <button className="btn" onClick={() => setMode("login")}>Login</button></>
        )}
      </p>
      <p className="helper" style={{ marginTop: 8 }}>
        Tip: demo user is <code>demo@user.com</code> / <code>demo123</code>
      </p>
    </div>
  );
}

/* ---------- Todos ---------- */
function Todos({ token, user, onLogout }) {
  const [hello, setHello] = useState("(loading...)");
  const [items, setItems] = useState([]);
  const [title, setTitle] = useState("");
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  const [total, setTotal] = useState(0);
  const lastPage = useMemo(() => Math.max(1, Math.ceil(total / limit)), [total, limit]);

  useEffect(() => {
    fetch(`${API}/hello`).then((r) => r.json()).then((d) => setHello(d.message)).catch(() => {});
  }, []);

  const load = async (p = page) => {
    try {
      const data = await api(`/todos?page=${p}&limit=${limit}`, { token });
      setItems(data.items || []);
      setPage(data.page || 1);
      setTotal(data.total || 0);
    } catch (err) {
      if (err.status === 401) { onLogout(); return; }
      throw err;
    }
  };

  useEffect(() => { load(1); }, []);

  const add = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    await api("/todos", { method: "POST", body: { title }, token });
    setTitle("");
    load(1);
  };

  const toggle = async (id) => {
    await api(`/todos/${id}/toggle`, { method: "PATCH", token });
    load();
  };

  const removeItem = async (id) => {
    await api(`/todos/${id}`, { method: "DELETE", token });
    const newCount = total - 1;
    const next = Math.min(page, Math.max(1, Math.ceil(newCount / limit)));
    load(next);
  };

  return (
    <div className="container">
      <div className="header">
        <h1>PyReactX</h1>
        <span className="badge">SQLite · JWT</span>
        <span className="spacer"></span>
        <span className="helper">Signed in as <b>{user.email}</b></span>
        <button className="btn" onClick={onLogout}>Logout</button>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h2 className="section-title">Status</h2>
        <p>{hello}</p>
      </div>

      <div className="card">
        <h2 className="section-title">Todos</h2>
        <form onSubmit={add} className="form">
          <input
            className="input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="New todo title"
          />
          <button className="btn btn-primary">Add</button>
        </form>

        <ul className="list">
          {items.map((t) => (
            <li key={t.id} className="item">
              <input type="checkbox" checked={t.done} onChange={() => toggle(t.id)} />
              <span className={`item-title ${t.done ? "done" : ""}`}>{t.title}</span>
              <button className="btn btn-danger" onClick={() => removeItem(t.id)}>Delete</button>
            </li>
          ))}
          {items.length === 0 && <li className="item helper">(no items)</li>}
        </ul>

        <div className="meta">
          <div className="grow"></div>
          <button className="btn" disabled={page <= 1} onClick={() => load(page - 1)}>Prev</button>
          <span>Page {page} of {lastPage}</span>
          <button className="btn" disabled={page >= lastPage} onClick={() => load(page + 1)}>Next</button>
          <span>{total} total</span>
        </div>
      </div>
    </div>
  );
}

/* ---------- App Root ---------- */
function AppRoot() {
  const [token, setToken] = useLocalStorage("pyreactx_token", "");
  const [user, setUser] = useLocalStorage("pyreactx_user", null);

  const onAuth = (t, u) => { setToken(t); setUser(u); };
  const onLogout = () => { setToken(""); setUser(null); };

  return (
    <div className="container">
      {token && user ? (
        <Todos token={token} user={user} onLogout={onLogout} />
      ) : (
        <Auth onAuth={onAuth} />
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<AppRoot />);
