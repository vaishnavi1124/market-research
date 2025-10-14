// // frontend/src/App.tsx
// import { useState } from "react";
// import Sidebar from "./components/Sidebar";
// import Dashboard from "./components/Dashboard";
// import Chatbot from "./components/Chatbot";
// import ResearchHeader from "./components/ResearchHeader";
// export default function App() {
//   const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
//   const [collapsed, setCollapsed] = useState(false);
//   const [newChatNonce, setNewChatNonce] = useState(0);

//   // bump this whenever history should refresh
//   const [historyRefreshNonce, setHistoryRefreshNonce] = useState(0);
//   const handleHistoryChange = () => setHistoryRefreshNonce((n) => n + 1);

//   return (
//     <div className="min-h-screen bg-gradient-to-br from-blue-200 via-yellow-100 to-red-200">
//       <ResearchHeader />
//       <Sidebar
//         currentTopic={selectedTopic}
//         onOpenTopic={(t) => setSelectedTopic(t)}
//         onNewChat={() => {
//           setSelectedTopic(null);
//           setNewChatNonce((n) => n + 1);
//           window.scrollTo({ top: 0, behavior: "smooth" });
//         }}
//         collapsed={collapsed}
//         onToggleCollapse={() => setCollapsed((c) => !c)}
//         refreshNonce={historyRefreshNonce}   // ✅ ok here (as a real prop)
//       />
//       {/* optional: Sidebar now refetches history when refreshNonce changes */}

//       <main className={`transition-all duration-200 ${collapsed ? "pl-20" : "pl-80"}`}>
//         <div className="max-w-6xl mx-auto p-6 md:p-10 space-y-1">
//           <Dashboard
//             selectedTopic={selectedTopic}
//             newChatNonce={newChatNonce}
//             onOpenedTopic={(t) => setSelectedTopic(t)}
//             onHistoryChange={handleHistoryChange}
//           />
//           {/* ✅ now provided to Dashboard */}

//           <h3 className="text-lg font-semibold text-slate-800 mb-3"></h3>

//           <Chatbot
//             topic={selectedTopic}
//             newChatNonce={newChatNonce}
//             onHistoryChange={handleHistoryChange}
//           />
//           {/* ✅ now provided to Chatbot */}
//         </div>
//       </main>
//     </div>
//   );
// }



// // src/App.tsx
// import { useCallback, useEffect, useState } from "react";
// import Auth from "./components/Auth";
// import Home from "./components/Home";
// import { api } from "./lib/api";
// import ResearchHeader from "./components/ResearchHeader";

// export type Me = {
//   id: number;
//   email: string;
//   full_name?: string | null;
//   status: "ACTIVE" | "INACTIVE" | "SUSPENDED";
//   last_login?: string | null;
//   register_date: string;
//   plan_type: "FREE" | "BASIC" | "PRO";
// };

// export default function App() {
//   const [me, setMe] = useState<Me | null>(null);
//   const [loading, setLoading] = useState(true);

//   const fetchMe = useCallback(async () => {
//     try {
//       const { data } = await api.get<Me>("/auth/me");
//       // If your backend returns 401 for unauthenticated, this line only runs when logged in.
//       // If it returns 200 with a guest payload, you may want to check a flag here.
//       setMe(data);
//     } catch {
//       setMe(null);
//     } finally {
//       setLoading(false);
//     }
//   }, []);

//   // Boot: check session
//   useEffect(() => {
//     fetchMe();
//   }, [fetchMe]);

//   // Refetch on window focus (useful if you log in on another tab)
//   useEffect(() => {
//     const onFocus = () => fetchMe();
//     window.addEventListener("focus", onFocus);
//     return () => window.removeEventListener("focus", onFocus);
//   }, [fetchMe]);

//   // Silent refresh every 10 min (defensive)
//   useEffect(() => {
//   if (!me) return; // only start if logged in
//   const t = setInterval(() => {
//     api.post("/auth/refresh").catch(() => setMe(null)); // force logout on 401
//   }, 10 * 60 * 1000);
//   return () => clearInterval(t);
// }, [me]);

//   const handleLogout = useCallback(async () => {
//     try {
//       await api.post("/auth/logout");
//     } finally {
//       setMe(null);
//     }
//   }, []);

//   if (loading) {
//     return (
//       <div className="min-h-screen grid place-items-center bg-gradient-to-br from-blue-200 via-yellow-100 to-red-200">
//         <div className="animate-pulse text-slate-600">Loading…</div>
//       </div>
//     );
//   }

//   // Not logged in → show Auth
//   if (!me) {
//     return (
//       <div className="min-h-screen bg-gradient-to-br from-blue-200 via-yellow-100 to-red-200">
//         <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
//           <ResearchHeader />
//         </div>
//         {/* onAuthed triggers fetchMe -> me becomes non-null -> Home renders */}
//         <Auth onAuthed={fetchMe} />
//       </div>
//     );
//   }

//   // Logged in → Home
//   return <Home me={me} onLogout={handleLogout} />;
// }


// src/App.tsx
import { useCallback, useEffect, useRef, useState } from "react";
import Auth from "./components/Auth";
import Home from "./components/Home";
import { api, safeGet, safePost } from "./lib/api";
import ResearchHeader from "./components/ResearchHeader";

export type Me = {
  id: number;
  email: string;
  full_name?: string | null;
  status: "ACTIVE" | "INACTIVE" | "SUSPENDED";
  last_login?: string | null;
  register_date: string;
  plan_type: "FREE" | "BASIC" | "PRO";
};

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  // simple gate to avoid rapid refetch storms
  const lastFetchRef = useRef<number>(0);

  const fetchMe = useCallback(async () => {
    const now = Date.now();
    if (now - lastFetchRef.current < 1500) return; // throttle
    lastFetchRef.current = now;

    const res = await safeGet<Me>("/auth/me");
    if (res.ok) {
      setMe(res.data);
    } else {
      setMe(null); // unauthenticated or expired -> show Auth
    }
    setLoading(false);
  }, []);

  // Boot: check session once
  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  // OPTIONAL: re-enable focus refresh later, but debounce it.
  // useEffect(() => {
  //   let t: any;
  //   const onFocus = () => {
  //     clearTimeout(t);
  //     t = setTimeout(fetchMe, 400);
  //   };
  //   window.addEventListener("focus", onFocus);
  //   return () => {
  //     window.removeEventListener("focus", onFocus);
  //     clearTimeout(t);
  //   };
  // }, [fetchMe]);

  // Silent refresh every 10 min — ONLY when logged in
  useEffect(() => {
    if (!me) return;
    const t = setInterval(() => {
      safePost("/auth/refresh").then((r) => {
        if (!r.ok) {
          // refresh failed -> drop to logged-out state
          setMe(null);
        }
      });
    }, 10 * 60 * 1000);
    return () => clearInterval(t);
  }, [me]);

  const handleLogout = useCallback(async () => {
    try {
      await api.post("/auth/logout"); // cookies cleared server-side
    } catch {
      // ignore
    } finally {
      setMe(null); // immediately reflect logout client-side
    }
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen grid place-items-center bg-gradient-to-br from-blue-200 via-yellow-100 to-red-200">
        <div className="animate-pulse text-slate-600">Loading…</div>
      </div>
    );
  }

  if (!me) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-200 via-yellow-100 to-red-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
          <ResearchHeader />
        </div>
        {/* onAuthed triggers fetchMe -> me becomes non-null -> Home renders */}
        <Auth onAuthed={fetchMe} />
      </div>
    );
  }

  return <Home me={me} onLogout={handleLogout} />;
}
