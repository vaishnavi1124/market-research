// src/components/Home.tsx
import { useCallback, useMemo, useState } from "react";
import ResearchHeader from "./ResearchHeader";
import Sidebar from "./Sidebar";
import Dashboard from "./Dashboard";
import Chatbot from "./Chatbot";
import { FiChevronDown, FiLogOut, FiMenu } from "react-icons/fi";

const API_BASE = (import.meta as any)?.env?.VITE_API_URL || "http://127.0.0.1:8000";

export type Me = {
  id: number;
  email: string;
  full_name?: string | null;
  status: "ACTIVE" | "INACTIVE" | "SUSPENDED";
  last_login?: string | null;
  register_date: string;
  plan_type: "FREE" | "BASIC" | "PRO";
};

export default function Home({
  me,
  onLogout,
}: {
  me: Me;
  onLogout: () => void;
}) {
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [newChatNonce, setNewChatNonce] = useState(0);
  const [historyRefreshNonce, setHistoryRefreshNonce] = useState(0);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  // ⬇️ Suggestions shared between Dashboard → Chatbot
  const [chatbotExternalSuggestions, setChatbotExternalSuggestions] = useState<
    string[] | null
  >(null);
  const [chatbotExternalIntro, setChatbotExternalIntro] = useState<string | null>(
    null
  );

  const handleHistoryChange = useCallback(
    () => setHistoryRefreshNonce((n) => n + 1),
    []
  );

  /**
   * Parse DB datetime strings robustly.
   * - If it's ISO with timezone -> use Date(raw) directly
   * - If it's naive MySQL "YYYY-MM-DD HH:mm:ss", treat it as IST wall time
   */
  const parseDbDate = (raw?: string | null) => {
    if (!raw) return null;
    const s = raw.trim();
    // ISO with TZ (e.g., 2025-08-25T11:30:27Z or +05:30)
    if (/[tT].*([zZ]|[+\-]\d{2}:\d{2})$/.test(s)) return new Date(s);

    // Naive -> assume IST; convert to a UTC instant that formats back to same IST time
    const parts = s.split(/[ T]/);
    if (parts.length < 2) return new Date(s);
    const [d, t] = parts;
    const [y, m, day] = d.split("-").map((n) => parseInt(n, 10));
    const [hh, mm, ss] = (t || "00:00:00").split(":").map((n) => parseInt(n, 10));
    const utcMs = Date.UTC(
      y,
      (m || 1) - 1,
      day || 1,
      (hh || 0) - 5,
      (mm || 0) - 30,
      ss || 0,
      0
    );
    return new Date(utcMs);
  };

  const fmt = (raw?: string | null, opts?: Intl.DateTimeFormatOptions) => {
    const d = parseDbDate(raw);
    if (!d) return "—";
    return new Intl.DateTimeFormat("en-IN", {
      dateStyle: "medium",
      timeStyle: "medium",
      timeZone: "Asia/Kolkata",
      ...opts,
    }).format(d);
  };

  const displayName = (me.full_name || "").trim() || me.email;
  const initials = displayName
    .split(" ")
    .map((s) => s[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  // New Chat clears topic + chatbot suggestions
  const onNewChat = () => {
    setSelectedTopic(null);
    setNewChatNonce((n) => n + 1);
    setChatbotExternalSuggestions(null);
    setChatbotExternalIntro(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // 🔐 Proper logout: call /auth/logout then clear local state
  const handleLogout = async () => {
    try {
      const resp = await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        credentials: "include", // send cookies so backend clears them
      });
      if (!resp.ok) throw new Error("Logout failed");
    } catch (err) {
      console.error("Logout error:", err);
    } finally {
      onLogout();
    }
  };

  // const handleLogout = async () => {
  //   try {
  //     await fetch(`${API_BASE}/auth/logout`, {
  //       method: "POST",
  //       credentials: "include",
  //     });
  //   } finally {
  //     onLogout(); // clears App state
  //   }
  // };

  
  const UserMenu = useMemo(
    () => (
      <div className="relative">
        <button
          onClick={() => setUserMenuOpen((o) => !o)}
          className="flex items-center gap-2 rounded-full border border-slate-200/60 bg-white/30 hover:bg-white/40 px-2.0 py-1 shadow-sm transition backdrop-blur"
          aria-haspopup="menu"
          aria-expanded={userMenuOpen}
        >
          <span className="grid h-7 w-7 place-items-center rounded-full bg-slate-900 text-white text-xs font-semibold">
            {initials}
          </span>
          <span className="hidden sm:block text-sm font-medium text-slate-800">
            {displayName}
          </span>
          <span className="hidden md:inline text-[11px] px-2 py-0.5 rounded-full bg-emerald-100/70 text-emerald-700 border border-emerald-200/70">
            {me.plan_type}
          </span>
          <FiChevronDown className="text-slate-500" />
        </button>

        {userMenuOpen && (
          <div
            role="menu"
            className="absolute right-0 mt-2 w-64 rounded-xl border border-slate-200/60 bg-white/70 shadow-lg backdrop-blur p-2 z-50"
          >
            <div className="px-3 py-2">
              <div className="text-xs text-slate-500">Signed in as</div>
              <div className="text-sm font-medium text-slate-800 truncate">
                {me.email}
              </div>
            </div>
            <div className="mx-2 my-2 h-px bg-slate-200/70" />
            <div className="px-3 py-2 text-xs text-slate-500">
              Last login: <span className="text-slate-700">{fmt(me.last_login)}</span>
            </div>
            <button
              onClick={handleLogout}
              className="w-full inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-rose-50 text-rose-700"
            >
              <FiLogOut /> Logout
            </button>
          </div>
        )}
      </div>
    ),
    [userMenuOpen, initials, displayName, me.email, me.plan_type, me.last_login]
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-200 via-yellow-100 to-red-200">
      {/* Soft, transparent gradient background */}
      <div aria-hidden className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute -top-32 -right-32 h-96 w-96 rounded-full bg-gradient-to-br from-blue-200/40 via-fuchsia-100/40 to-rose-100/40 blur-3xl" />
        <div className="absolute -bottom-36 -left-24 h-[28rem] w-[28rem] rounded-full bg-gradient-to-tr from-emerald-100/40 via-cyan-100/40 to-indigo-100/40 blur-3xl" />
      </div>

      {/* Top App Bar (no New Chat button) */}
      <header className="sticky top-0 z-40 backdrop-blur bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-600 border-b border-slate-200/50">
        <div className="max-w-7xl mx-auto h-14 px-3 sm:px-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCollapsed((c) => !c)}
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg hover:bg-white/40 text-slate-700 backdrop-blur"
              aria-label="Toggle sidebar"
            >
              <FiMenu />
            </button>
            <div className="hidden sm:flex items-center gap-3">
              <div className="text-white font-semibold">SmartResearch</div>
              {selectedTopic && (
                <div className="hidden md:flex items-center text-sm text-slate-200">
                  <span className="mx-2">/</span>
                  <span className="truncate max-w-[20ch]">{selectedTopic}</span>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">{UserMenu}</div>
        </div>
      </header>

      {/* Sidebar */}
      <Sidebar
        currentTopic={selectedTopic}
        onOpenTopic={(t) => setSelectedTopic(t)}
        onNewChat={onNewChat}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((c) => !c)}
        refreshNonce={historyRefreshNonce}
      />

      {/* Main Content */}
      <main className={`transition-all duration-200 ${collapsed ? "pl-20" : "pl-80"}`}>
        {/* Product header (transparent card) */}
        <div className="bg-transparent p-1 md:p-1">
          <ResearchHeader
            compact
            sticky={false}
            subtitle="AI-driven Market & Competitive Intelligence"
          />
        </div>

        {/* Dashboard */}
        <Dashboard
          selectedTopic={selectedTopic}
          newChatNonce={newChatNonce}
          onOpenedTopic={(t) => setSelectedTopic(t)}
          onHistoryChange={handleHistoryChange}
          // pass setters so Dashboard can push suggestions into Chatbot
          setChatbotExternalSuggestions={setChatbotExternalSuggestions}
          setChatbotExternalIntro={setChatbotExternalIntro}
        />

        {/* Chatbot */}
        <Chatbot
          topic={selectedTopic}
          newChatNonce={newChatNonce}
          onHistoryChange={handleHistoryChange}
          // receive suggestions coming from Dashboard
          externalSuggestions={chatbotExternalSuggestions}
          externalIntroText={chatbotExternalIntro}
        />

        {/* Footer */}
        <footer className="py-1 text-center text-xs text-slate-500">
          © {new Date().getFullYear()} GenIntel · All rights reserved
        </footer>
      </main>

      {/* Click-away for user menu */}
      {userMenuOpen && (
        <div
          className="fixed inset-0 z-30"
          onClick={() => setUserMenuOpen(false)}
          aria-hidden
        />
      )}
    </div>
  );
}
