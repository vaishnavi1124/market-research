// src/components/Auth.tsx
import React, { useState } from "react";
import { api } from "../lib/api";
import {
  FaEye, FaEyeSlash, FaGoogle, FaLinkedin, FaUser, FaEnvelope, FaLock, FaBroom,
} from "react-icons/fa";
import { Button, Spinner, Form } from "react-bootstrap";

export default function Auth({ onAuthed }: { onAuthed?: () => void }): JSX.Element {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [planType, setPlanType] = useState<"FREE" | "BASIC" | "PRO">("FREE");
  const [confirm, setConfirm] = useState("");
  const [remember, setRemember] = useState(true);
  const [msg, setMsg] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const [showPass, setShowPass] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const reset = () => {
    setEmail(""); setPassword(""); setFullName(""); setPlanType("FREE");
    setConfirm(""); setMsg(""); setShowPass(false); setShowConfirm(false);
  };

  const handleRegister = async () => {
    if (!email || !password) return setMsg("Email and password are required.");
    if (password.length < 8) return setMsg("Password must be at least 8 characters.");
    if (password !== confirm) return setMsg("Passwords do not match.");
    try {
      setBusy(true);
      setMsg("");
      await api.post("/auth/register", {
        email,
        password,
        full_name: fullName || undefined,
        plan_type: planType,
        remember, // if your backend cares about cookie max-age
      });
      // Auto-login after register
      await api.post(
        "/auth/login",
        new URLSearchParams({ username: email, password, remember: String(remember) })
      );
      setMsg("");
      onAuthed?.(); // App will fetch /auth/me and render Home
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      if (e?.response?.status === 409) {
        setMsg("This email is already registered. Please sign in.");
      } else {
        setMsg(detail || "Registration failed");
      }
    } finally {
      setBusy(false);
    }
  };

  const handleLogin = async () => {
    if (!email || !password) return setMsg("Email and password are required.");
    try {
      setBusy(true);
      setMsg("");
      await api.post(
        "/auth/login",
        new URLSearchParams({ username: email, password, remember: String(remember) })
      );
      setMsg("");
      onAuthed?.(); // App fetches /auth/me -> Home
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || e?.message || "Login failed");
    } finally {
      setBusy(false);
    }
  };

  const onEnterSubmit = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      if (busy) return;
      (mode === "login" ? handleLogin() : handleRegister());
    }
  };

  return (
    <section className="min-h-[80vh] flex items-center">
      <div className="container px-6 py-12">
        <div className="g-6 flex flex-wrap items-center justify-center lg:justify-between">
          <div className="mb-12 md:mb-0 md:w-7/12 lg:w-6/12">
            <img
              src="https://tecdn.b-cdn.net/img/Photos/new-templates/bootstrap-login-form/draw2.svg"
              className="w-full"
              alt="Illustration"
            />
          </div>

          <div className="md:w-8/12 lg:ml-6 lg:w-5/12">
            {/* Toggle */}
            <div className="flex gap-2 mb-6">
              <Button
                variant={mode === "login" ? "primary" : "light"}
                onClick={() => { setMode("login"); reset(); }}
              >
                Sign in
              </Button>
              <Button
                variant={mode === "register" ? "primary" : "light"}
                onClick={() => { setMode("register"); reset(); }}
              >
                Create account
              </Button>
            </div>

            {/* Form */}
            <form onSubmit={(e) => e.preventDefault()} className="space-y-3">
              {mode === "register" && (
                <div>
                  <label className="block text-sm font-medium mb-1">Full name</label>
                  <div className="relative">
                    <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                      <FaUser />
                    </div>
                    <input
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      onKeyDown={onEnterSubmit}
                      className="w-full rounded border border-gray-300 pl-9 pr-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Your full name"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium mb-1">Email address</label>
                <div className="relative">
                  <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                    <FaEnvelope />
                  </div>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onKeyDown={onEnterSubmit}
                    className="w-full rounded border border-gray-300 pl-9 pr-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="you@example.com"
                    autoComplete="email"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Password</label>
                <div className="relative">
                  <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                    <FaLock />
                  </div>
                  <input
                    type={showPass ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyDown={onEnterSubmit}
                    className="w-full rounded border border-gray-300 pl-9 pr-10 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="••••••••"
                    autoComplete={mode === "login" ? "current-password" : "new-password"}
                  />
                  <button
                    type="button"
                    aria-label={showPass ? "Hide password" : "Show password"}
                    onClick={() => setShowPass((s) => !s)}
                    className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-500 hover:text-slate-700"
                    tabIndex={-1}
                  >
                    {showPass ? <FaEyeSlash /> : <FaEye />}
                  </button>
                </div>
              </div>

              {mode === "register" && (
                <>
                  <div>
                    <label className="block text-sm font-medium mb-1">Confirm password</label>
                    <div className="relative">
                      <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
                        <FaLock />
                      </div>
                      <input
                        type={showConfirm ? "text" : "password"}
                        value={confirm}
                        onChange={(e) => setConfirm(e.target.value)}
                        onKeyDown={onEnterSubmit}
                        className="w-full rounded border border-gray-300 pl-9 pr-10 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="••••••••"
                        autoComplete="new-password"
                      />
                      <button
                        type="button"
                        aria-label={showConfirm ? "Hide confirm password" : "Show confirm password"}
                        onClick={() => setShowConfirm((s) => !s)}
                        className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-500 hover:text-slate-700"
                        tabIndex={-1}
                      >
                        {showConfirm ? <FaEyeSlash /> : <FaEye />}
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">Plan</label>
                    <select
                      className="w-full border rounded px-3 py-2 outline-none focus:ring-2 focus:ring-blue-500"
                      value={planType}
                      onChange={(e) => setPlanType(e.target.value as any)}
                    >
                      <option value="FREE">FREE</option>
                      <option value="BASIC">BASIC</option>
                      <option value="PRO">PRO</option>
                    </select>
                  </div>
                </>
              )}

              <div className="mb-2 flex items-center justify-between">
                <Form.Check
                  type="checkbox"
                  id="remember"
                  label="Remember me"
                  checked={remember}
                  onChange={() => setRemember((r) => !r)}
                />
                <a href="#!" className="text-primary text-sm">Forgot password?</a>
              </div>

              {/* ACTION BUTTONS */}
              <div className="d-flex gap-2">
                <Button
                  variant="primary"
                  className="flex-fill"
                  onClick={mode === "login" ? handleLogin : handleRegister}
                  disabled={busy}
                >
                  {busy ? <Spinner animation="border" size="sm" /> : (mode === "login" ? "Sign In" : "Create Account")}
                </Button>

                <Button
                  variant="outline-secondary"
                  className="flex-fill d-flex align-items-center justify-content-center gap-2"
                  onClick={reset}
                  disabled={busy}
                >
                  <FaBroom /> Clear
                </Button>
              </div>

              {msg && <p className="mt-2 text-sm text-rose-600">{msg}</p>}
            </form>

            {/* Divider + Social */}
            <div className="my-4 d-flex align-items-center">
              <div className="flex-grow border-top" />
              <span className="px-3 text-muted">OR</span>
              <div className="flex-grow border-top" />
            </div>

            <div className="d-flex gap-2">
              <Button variant="dark" className="flex-fill d-flex align-items-center justify-content-center gap-2">
                <FaGoogle /> Continue with Google
              </Button>
              <Button variant="primary" className="flex-fill d-flex align-items-center justify-content-center gap-2">
                <FaLinkedin /> Continue with LinkedIn
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
