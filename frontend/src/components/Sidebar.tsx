// // frontend\src\components\Sidebar.tsx
// import { useEffect, useMemo, useRef, useState } from "react";
// import {
//   FaComments,
//   FaPlus,
//   FaEllipsisV,
//   FaShareAlt,
//   FaPen,
//   FaArchive,
//   FaTrash,
//   FaChevronLeft,
//   FaChevronRight,
// } from "react-icons/fa";

// const API_BASE = "http://127.0.0.1:8000";

// type TopicRow = { topic: string; last_at: string; count: number };

// interface SidebarProps {
//   currentTopic: string | null;
//   onOpenTopic: (topic: string) => void;
//   onNewChat: () => void;
//   collapsed: boolean;
//   onToggleCollapse: () => void;

//   // 🆕 bump this from App to force a refresh (e.g., after send/report)
//   refreshNonce?: number;
// }

// export default function Sidebar({
//   currentTopic,
//   onOpenTopic,
//   onNewChat,
//   collapsed,
//   onToggleCollapse,
//   refreshNonce, // 🆕
// }: SidebarProps) {
//   const [topics, setTopics] = useState<TopicRow[] | null>(null);
//   const [error, setError] = useState<string | null>(null);
//   const [menuOpenFor, setMenuOpenFor] = useState<string | null>(null);
//   const menusRef = useRef<Map<string, HTMLDivElement | null>>(new Map());

//   // cache: topic -> report id
//   const reportIdCache = useMemo(() => new Map<string, number | null>(), []);

//   const loadHistory = async () => {
//     setError(null);
//     try {
//       const res = await fetch(`${API_BASE}/api/chat-history`);
//       if (!res.ok) throw new Error("Failed to load history");
//       const data: TopicRow[] = await res.json();
//       setTopics(data);
//     } catch (e: any) {
//       setError(e?.message || "Failed to load history");
//       setTopics([]);
//     }
//   };

//   // initial load
//   useEffect(() => {
//     loadHistory();
//   }, []);

//   // 🆕 refresh when parent bumps the nonce
//   useEffect(() => {
//     if (typeof refreshNonce === "number") {
//       // invalidate id cache so rename/delete/archival stays consistent
//       reportIdCache.clear();
//       loadHistory();
//     }
//     // eslint-disable-next-line react-hooks/exhaustive-deps
//   }, [refreshNonce]);

//   // close menus on outside click
//   useEffect(() => {
//     function handleDocClick(e: MouseEvent) {
//       if (!menuOpenFor) return;
//       const el = menusRef.current.get(menuOpenFor);
//       if (el && !el.contains(e.target as Node)) setMenuOpenFor(null);
//     }
//     document.addEventListener("click", handleDocClick);
//     return () => document.removeEventListener("click", handleDocClick);
//   }, [menuOpenFor]);

//   async function getReportIdForTopic(topic: string): Promise<number | null> {
//     if (reportIdCache.has(topic)) return reportIdCache.get(topic)!;
//     try {
//       const r = await fetch(
//         `${API_BASE}/api/report-by-topic?topic=${encodeURIComponent(topic)}`
//       );
//       if (!r.ok) {
//         reportIdCache.set(topic, null);
//         return null;
//       }
//       const data = await r.json();
//       const id = typeof data?.id === "number" ? data.id : null;
//       reportIdCache.set(topic, id);
//       return id;
//     } catch {
//       reportIdCache.set(topic, null);
//       return null;
//     }
//   }

//   const fetchChatIds = async (topic: string): Promise<number[]> => {
//     try {
//       const r = await fetch(
//         `${API_BASE}/api/chat-thread?topic=${encodeURIComponent(topic)}`
//       );
//     if (!r.ok) return [];
//       const rows = (await r.json()) as Array<{ id: number }>;
//       return rows.map((m) => m.id);
//     } catch {
//       return [];
//     }
//   };

//   async function cascadeRename(topic: string, newName: string, rid: number) {
//     // rename report
//     await fetch(`${API_BASE}/api/history/action`, {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify({
//         kind: "report",
//         id: rid,
//         action: "rename",
//         value: newName,
//       }),
//     });

//     // rename all chat rows under topic
//     const ids = await fetchChatIds(topic);
//     for (const id of ids) {
//       await fetch(`${API_BASE}/api/history/action`, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({
//           kind: "chat",
//           id,
//           action: "rename",
//           value: newName,
//         }),
//       });
//     }
//   }

//   async function cascadeMark(topic: string, rid: number, action: "archive" | "delete") {
//     // report
//     await fetch(`${API_BASE}/api/history/action`, {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify({ kind: "report", id: rid, action }),
//     });

//     // chats
//     const ids = await fetchChatIds(topic);
//     for (const id of ids) {
//       await fetch(`${API_BASE}/api/history/action`, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ kind: "chat", id, action }),
//       });
//     }
//   }

//   async function doAction(
//     topic: string,
//     action: "share" | "rename" | "archive" | "delete"
//   ) {
//     try {
//       const rid = await getReportIdForTopic(topic);
//       if (!rid && action !== "delete" && action !== "archive") {
//         alert("No report found for this topic.");
//         return;
//       }

//       if (action === "share") {
//         const r = await fetch(`${API_BASE}/api/history/action`, {
//           method: "POST",
//           headers: { "Content-Type": "application/json" },
//           body: JSON.stringify({ kind: "report", id: rid, action: "share" }),
//         });
//         const j = await r.json().catch(() => ({}));
//         if (!r.ok) throw new Error(j?.error || "Failed to share");
//         const full = window.location.origin + (j?.share_url || "");
//         try {
//           await navigator.clipboard.writeText(full);
//           alert("Share link copied:\n" + full);
//         } catch {
//           prompt("Share link (copy):", full);
//         }
//         setMenuOpenFor(null);
//         return;
//       }

//       if (action === "rename") {
//         const newName = prompt("New topic name:", topic);
//         if (!newName || newName.trim() === "" || newName.trim() === topic) {
//           setMenuOpenFor(null);
//           return;
//         }
//         await cascadeRename(topic, newName.trim(), rid!);
//         reportIdCache.delete(topic);
//         setMenuOpenFor(null);
//         await loadHistory();
//         if (currentTopic === topic) onOpenTopic(newName.trim());
//         return;
//       }

//       if (action === "archive") {
//         if (!confirm("Archive this topic (report + chat)?")) {
//           setMenuOpenFor(null);
//           return;
//         }
//         if (rid) await cascadeMark(topic, rid, "archive");
//         setMenuOpenFor(null);
//         await loadHistory();
//         if (currentTopic === topic) onNewChat();
//         return;
//       }

//       if (action === "delete") {
//         if (!confirm("Delete this topic permanently (report + chat)?")) {
//           setMenuOpenFor(null);
//           return;
//         }
//         if (rid) await cascadeMark(topic, rid, "delete");
//         setMenuOpenFor(null);
//         await loadHistory();
//         if (currentTopic === topic) onNewChat();
//         return;
//       }
//     } catch (e: any) {
//       alert(e?.message || "Action failed");
//     }
//   }

//   const widthClass = collapsed ? "w-16" : "w-72";

//   return (
//     <aside
//       className={`${widthClass} fixed left-0 top-0 h-screen bg-white/90 backdrop-blur border-r border-slate-200 text-slate-800 flex flex-col p-3 transition-all duration-200 z-30`}
//     >
//       {/* Header with collapse/expand */}
//       <div className="flex items-center justify-between mb-3">
//         {!collapsed ? (
//           <h2 className="text-sm font-semibold flex items-center gap-2 text-slate-700">
//             <FaComments /> History
//           </h2>
//         ) : (
//           <div className="w-6 h-6" aria-hidden />
//         )}
//         <button
//           onClick={onToggleCollapse}
//           className="text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-md p-2"
//           title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
//         >
//           {collapsed ? <FaChevronRight /> : <FaChevronLeft />}
//         </button>
//       </div>

//       {/* History list */}
//       <div className="flex-1 overflow-y-auto space-y-2 pr-1">
//         {error && !collapsed && (
//           <div className="text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded p-2">
//             {error}
//           </div>
//         )}
//         {topics === null && !collapsed && (
//           <div className="text-xs text-slate-500">Loading…</div>
//         )}
//         {topics && topics.length === 0 && !collapsed && (
//           <div className="text-xs text-slate-500">
//             No history yet. Generate a report or ask a question.
//           </div>
//         )}

//         {topics &&
//           topics.map((t) => {
//             const active = currentTopic === t.topic;
//             const isOpen = menuOpenFor === t.topic;

//             return (
//               <div key={`${t.topic}-${t.last_at}`} className="relative">
//                 <button
//                   onClick={() => onOpenTopic(t.topic)}
//                   className={`w-full text-left rounded-lg transition group ${
//                     active
//                       ? "bg-indigo-100 border border-indigo-200"
//                       : "bg-white border border-slate-200 hover:bg-slate-50"
//                   } ${collapsed ? "p-2" : "p-3"}`}
//                   title={t.topic}
//                 >
//                   <div className="flex items-start justify-between gap-2">
//                     {/* Left: avatar + text */}
//                     <div className="flex items-center gap-2 min-w-0">
//                       <div className="w-7 h-7 rounded-full bg-indigo-500/90 text-white flex items-center justify-center text-xs font-bold">
//                         {t.topic?.[0]?.toUpperCase() || "T"}
//                       </div>
//                       {!collapsed && (
//                         <div className="min-w-0">
//                           <div className="text-sm truncate font-medium text-slate-800">
//                             {t.topic}
//                           </div>
//                           <div className="text-[11px] text-slate-500 mt-0.5 truncate">
//                             {new Date(t.last_at).toLocaleString()} • {t.count} items
//                           </div>
//                         </div>
//                       )}
//                     </div>

//                     {/* menu toggle */}
//                     {!collapsed && (
//                       <button
//                         type="button"
//                         onClick={(e) => {
//                           e.stopPropagation();
//                           setMenuOpenFor((prev) =>
//                             prev === t.topic ? null : t.topic
//                           );
//                         }}
//                         className="opacity-90 hover:opacity-100 text-slate-500 px-2 py-1 rounded-md hover:bg-slate-100"
//                         title="More"
//                       >
//                         <FaEllipsisV />
//                       </button>
//                     )}
//                   </div>
//                 </button>

//                 {/* Flyout menu */}
//                 {isOpen && !collapsed && (
//                   <div
//                     ref={(el) => {
//                       menusRef.current.set(t.topic, el);
//                     }}
//                     className="absolute right-2 top-12 z-30 bg-white border border-slate-200 rounded-lg shadow-lg w-44 py-1"
//                   >
//                     <MenuBtn
//                       label="Share"
//                       icon={<FaShareAlt />}
//                       onClick={() => doAction(t.topic, "share")}
//                     />
//                     <MenuBtn
//                       label="Rename"
//                       icon={<FaPen />}
//                       onClick={() => doAction(t.topic, "rename")}
//                     />
//                     <MenuBtn
//                       label="Archive"
//                       icon={<FaArchive />}
//                       onClick={() => doAction(t.topic, "archive")}
//                     />
//                     <MenuBtn
//                       label="Delete"
//                       icon={<FaTrash />}
//                       danger
//                       onClick={() => doAction(t.topic, "delete")}
//                     />
//                   </div>
//                 )}
//               </div>
//             );
//           })}
//       </div>

//       {/* New Chat */}
//       <button
//         onClick={() => onNewChat()}
//         className={`mt-3 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm py-2 px-3 rounded-lg shadow-sm transition-colors ${
//           collapsed ? "px-0" : ""
//         }`}
//         title="New Chat"
//       >
//         <FaPlus />
//         {!collapsed && <span>New Chat</span>}
//       </button>
//     </aside>
//   );
// }

// function MenuBtn({
//   label,
//   icon,
//   onClick,
//   danger,
// }: {
//   label: string;
//   icon: React.ReactNode;
//   onClick: () => void;
//   danger?: boolean;
// }) {
//   return (
//     <button
//       type="button"
//       className={`w-full text-left px-3 py-2 text-sm flex items-center gap-2 hover:bg-slate-50 ${
//         danger ? "text-rose-600 hover:text-rose-700" : "text-slate-700"
//       }`}
//       onClick={(e) => {
//         e.stopPropagation();
//         onClick();
//       }}
//     >
//       <span className="text-xs">{icon}</span>
//       {label}
//     </button>
//   );
// }


// // frontend/src/components/Sidebar.tsx
// import { useEffect, useMemo, useRef, useState } from "react";
// import {
//   FaComments,
//   FaPlus,
//   FaEllipsisV,
//   FaShareAlt,
//   FaPen,
//   FaArchive,
//   FaTrash,
//   FaChevronLeft,
//   FaChevronRight,
//   FaDownload,            // 🆕
// } from "react-icons/fa";

// const API_BASE = "http://127.0.0.1:8000";

// type TopicRow = { topic: string; last_at: string; count: number };

// interface SidebarProps {
//   currentTopic: string | null;
//   onOpenTopic: (topic: string) => void;
//   onNewChat: () => void;
//   collapsed: boolean;
//   onToggleCollapse: () => void;
//   refreshNonce?: number; // bump this from App to force refresh
// }

// export default function Sidebar({
//   currentTopic,
//   onOpenTopic,
//   onNewChat,
//   collapsed,
//   onToggleCollapse,
//   refreshNonce,
// }: SidebarProps) {
//   const [topics, setTopics] = useState<TopicRow[] | null>(null);
//   const [error, setError] = useState<string | null>(null);
//   const [menuOpenFor, setMenuOpenFor] = useState<string | null>(null);
//   const menusRef = useRef<Map<string, HTMLDivElement | null>>(new Map());

//   // cache: topic -> report id
//   const reportIdCache = useMemo(() => new Map<string, number | null>(), []);

//   const loadHistory = async () => {
//     setError(null);
//     try {
//       const res = await fetch(`${API_BASE}/api/chat-history`);
//       if (!res.ok) throw new Error("Failed to load history");
//       const data: TopicRow[] = await res.json();
//       setTopics(data);
//     } catch (e: any) {
//       setError(e?.message || "Failed to load history");
//       setTopics([]);
//     }
//   };

//   // initial load
//   useEffect(() => {
//     loadHistory();
//   }, []);

//   // refresh when parent bumps the nonce
//   useEffect(() => {
//     if (typeof refreshNonce === "number") {
//       reportIdCache.clear(); // invalidate id cache so rename/delete stay consistent
//       loadHistory();
//     }
//     // eslint-disable-next-line react-hooks/exhaustive-deps
//   }, [refreshNonce]);

//   // close menus on outside click
//   useEffect(() => {
//     function handleDocClick(e: MouseEvent) {
//       if (!menuOpenFor) return;
//       const el = menusRef.current.get(menuOpenFor);
//       if (el && !el.contains(e.target as Node)) setMenuOpenFor(null);
//     }
//     document.addEventListener("click", handleDocClick);
//     return () => document.removeEventListener("click", handleDocClick);
//   }, [menuOpenFor]);

//   async function getReportIdForTopic(topic: string): Promise<number | null> {
//     if (reportIdCache.has(topic)) return reportIdCache.get(topic)!;
//     try {
//       const r = await fetch(
//         `${API_BASE}/api/report-by-topic?topic=${encodeURIComponent(topic)}`
//       );
//       if (!r.ok) {
//         reportIdCache.set(topic, null);
//         return null;
//       }
//       const data = await r.json();
//       const id = typeof data?.id === "number" ? data.id : null;
//       reportIdCache.set(topic, id);
//       return id;
//     } catch {
//       reportIdCache.set(topic, null);
//       return null;
//     }
//   }

//   const fetchChatIds = async (topic: string): Promise<number[]> => {
//     try {
//       const r = await fetch(
//         `${API_BASE}/api/chat-thread?topic=${encodeURIComponent(topic)}`
//       );
//       if (!r.ok) return [];
//       const rows = (await r.json()) as Array<{ id: number }>;
//       return rows.map((m) => m.id);
//     } catch {
//       return [];
//     }
//   };

//   // 🆕 utilities for download
//   function sanitizeFilename(name: string) {
//     return name.replace(/[\\/:*?"<>|]/g, "_").slice(0, 120);
//   }
//   async function downloadBlob(blob: Blob, filename: string) {
//     const url = URL.createObjectURL(blob);
//     try {
//       const a = document.createElement("a");
//       a.href = url;
//       a.download = filename;
//       document.body.appendChild(a);
//       a.click();
//       a.remove();
//     } finally {
//       URL.revokeObjectURL(url);
//     }
//   }
//   async function downloadUrlAs(url: string, filename: string) {
//     const resp = await fetch(url);
//     if (!resp.ok) throw new Error("Failed to fetch file for download");
//     const blob = await resp.blob();
//     await downloadBlob(blob, filename);
//   }

//   async function cascadeRename(topic: string, newName: string, rid: number) {
//     // rename report
//     await fetch(`${API_BASE}/api/history/action`, {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify({
//         kind: "report",
//         id: rid,
//         action: "rename",
//         value: newName,
//       }),
//     });

//     // rename all chat rows under topic
//     const ids = await fetchChatIds(topic);
//     for (const id of ids) {
//       await fetch(`${API_BASE}/api/history/action`, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({
//           kind: "chat",
//           id,
//           action: "rename",
//           value: newName,
//         }),
//       });
//     }
//   }

//   async function cascadeMark(topic: string, rid: number, action: "archive" | "delete") {
//     // report
//     await fetch(`${API_BASE}/api/history/action`, {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify({ kind: "report", id: rid, action }),
//     });

//     // chats
//     const ids = await fetchChatIds(topic);
//     for (const id of ids) {
//       await fetch(`${API_BASE}/api/history/action`, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ kind: "chat", id, action }),
//       });
//     }
//   }

//   async function doAction(
//     topic: string,
//     action: "share" | "rename" | "archive" | "delete" | "download" // 🆕
//   ) {
//     try {
//       const rid = await getReportIdForTopic(topic);
//       if (!rid && action !== "delete" && action !== "archive" && action !== "download") {
//         alert("No report found for this topic.");
//         return;
//       }

//       if (action === "download") {
//         // Try to download the PDF first, else fallback to markdown, else thread JSON
//         const resp = await fetch(
//           `${API_BASE}/api/report-by-topic?topic=${encodeURIComponent(topic)}`
//         );
//         if (!resp.ok) throw new Error("Unable to fetch report for download");
//         const data = await resp.json();
//         const safe = sanitizeFilename(topic);

//         const pdfUrlRaw: string | undefined =
//           data?.pdf_url || data?.pdf || data?.pdfPath;
//         const reportText: string | undefined =
//           data?.report || data?.research || data?.content;

//         if (pdfUrlRaw) {
//           const pdfUrl =
//             pdfUrlRaw.startsWith("http")
//               ? pdfUrlRaw
//               : `${API_BASE}${pdfUrlRaw.startsWith("/") ? pdfUrlRaw : `/${pdfUrlRaw}`}`;
//           await downloadUrlAs(pdfUrl, `${safe}.pdf`);
//         } else if (typeof reportText === "string" && reportText.trim()) {
//           const mdBlob = new Blob([reportText], {
//             type: "text/markdown;charset=utf-8",
//           });
//           await downloadBlob(mdBlob, `${safe}.md`);
//         } else {
//           // fallback: download full chat thread as JSON
//           const threadResp = await fetch(
//             `${API_BASE}/api/chat-thread?topic=${encodeURIComponent(topic)}`
//           );
//           if (!threadResp.ok) throw new Error("Unable to fetch chat thread");
//           const thread = await threadResp.json();
//           const jsonBlob = new Blob([JSON.stringify(thread, null, 2)], {
//             type: "application/json;charset=utf-8",
//           });
//           await downloadBlob(jsonBlob, `${safe}-thread.json`);
//         }

//         setMenuOpenFor(null);
//         return;
//       }

//       if (action === "share") {
//         const r = await fetch(`${API_BASE}/api/history/action`, {
//           method: "POST",
//           headers: { "Content-Type": "application/json" },
//           body: JSON.stringify({ kind: "report", id: rid, action: "share" }),
//         });
//         const j = await r.json().catch(() => ({}));
//         if (!r.ok) throw new Error(j?.error || "Failed to share");
//         const full = window.location.origin + (j?.share_url || "");
//         try {
//           await navigator.clipboard.writeText(full);
//           alert("Share link copied:\n" + full);
//         } catch {
//           prompt("Share link (copy):", full);
//         }
//         setMenuOpenFor(null);
//         return;
//       }

//       if (action === "rename") {
//         const newName = prompt("New topic name:", topic);
//         if (!newName || newName.trim() === "" || newName.trim() === topic) {
//           setMenuOpenFor(null);
//           return;
//         }
//         await cascadeRename(topic, newName.trim(), rid!);
//         reportIdCache.delete(topic);
//         setMenuOpenFor(null);
//         await loadHistory();
//         if (currentTopic === topic) onOpenTopic(newName.trim());
//         return;
//       }

//       if (action === "archive") {
//         if (!confirm("Archive this topic (report + chat)?")) {
//           setMenuOpenFor(null);
//           return;
//         }
//         if (rid) await cascadeMark(topic, rid, "archive");
//         setMenuOpenFor(null);
//         await loadHistory();
//         if (currentTopic === topic) onNewChat();
//         return;
//       }

//       if (action === "delete") {
//         if (!confirm("Delete this topic permanently (report + chat)?")) {
//           setMenuOpenFor(null);
//           return;
//         }
//         if (rid) await cascadeMark(topic, rid, "delete");
//         setMenuOpenFor(null);
//         await loadHistory();
//         if (currentTopic === topic) onNewChat();
//         return;
//       }
//     } catch (e: any) {
//       alert(e?.message || "Action failed");
//     }
//   }

//   const widthClass = collapsed ? "w-16" : "w-72";

//   return (
//     <aside
//       className={`${widthClass} fixed left-0 top-14 h-[calc(100vh-3.5rem)] bg-gradient-to-br from-blue-200 via-yellow-100 to-red-200 backdrop-blur border-r border-slate-200 text-slate-800 flex flex-col p-3 transition-all duration-200 z-30`}
//     >
//       {/* Header with collapse/expand */}
//       <div className="flex items-center justify-between mb-3">
//         {!collapsed ? (
//           <h2 className="text-sm font-semibold flex items-center gap-2 text-slate-700">
//             <FaComments /> History
//           </h2>
//         ) : (
//           <div className="w-6 h-6" aria-hidden />
//         )}
//         <button
//           onClick={onToggleCollapse}
//           className="text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-md p-2"
//           title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
//         >
//           {collapsed ? <FaChevronRight /> : <FaChevronLeft />}
//         </button>
//       </div>

//       {/* History list */}
//       <div className="flex-1 overflow-y-auto space-y-2 pr-1">
//         {error && !collapsed && (
//           <div className="text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded p-2">
//             {error}
//           </div>
//         )}
//         {topics === null && !collapsed && (
//           <div className="text-xs text-slate-500">Loading…</div>
//         )}
//         {topics && topics.length === 0 && !collapsed && (
//           <div className="text-xs text-slate-500">
//             No history yet. Generate a report or ask a question.
//           </div>
//         )}

//         {topics &&
//           topics.map((t) => {
//             const active = currentTopic === t.topic;
//             const isOpen = menuOpenFor === t.topic;
//             return (
//               <div key={`${t.topic}-${t.last_at}`} className="relative">
//                 <button
//                   onClick={() => onOpenTopic(t.topic)}
//                   className={`w-full text-left rounded-lg transition group ${active
//                       ? "bg-indigo-100 border border-indigo-200"
//                       : "bg-white border border-slate-200 hover:bg-slate-50"
//                     } ${collapsed ? "p-2" : "p-3"}`}
//                   title={t.topic}
//                 >
//                   <div className="flex items-start justify-between gap-2">
//                     {/* Left: avatar + text */}
//                     <div className="flex items-center gap-2 min-w-0">
//                       <div className="w-7 h-7 rounded-full bg-indigo-500/90 text-white flex items-center justify-center text-xs font-bold">
//                         {t.topic?.[0]?.toUpperCase() || "T"}
//                       </div>
//                       {!collapsed && (
//                         <div className="min-w-0">
//                           <div className="text-sm truncate font-medium text-slate-800">
//                             {t.topic}
//                           </div>
//                           <div className="text-[11px] text-slate-500 mt-0.5 truncate">
//                             {new Date(t.last_at).toLocaleString()} • {t.count} items
//                           </div>
//                         </div>
//                       )}
//                     </div>

//                     {/* menu toggle */}
//                     {!collapsed && (
//                       <button
//                         type="button"
//                         onClick={(e) => {
//                           e.stopPropagation();
//                           setMenuOpenFor((prev) =>
//                             prev === t.topic ? null : t.topic
//                           );
//                         }}
//                         className="opacity-90 hover:opacity-100 text-slate-500 px-2 py-1 rounded-md hover:bg-slate-100"
//                         title="More"
//                       >
//                         <FaEllipsisV />
//                       </button>
//                     )}
//                   </div>
//                 </button>

//                 {/* Flyout menu */}
//                 {isOpen && !collapsed && (
//                   <div
//                     ref={(el) => {
//                       menusRef.current.set(t.topic, el);
//                     }}
//                     className="absolute right-2 top-12 z-30 bg-white border border-slate-200 rounded-lg shadow-lg w-44 py-1"
//                   >
//                     <MenuBtn
//                       label="Download"                   // 🆕
//                       icon={<FaDownload />}
//                       onClick={() => doAction(t.topic, "download")}
//                     />
//                     <MenuBtn
//                       label="Share"
//                       icon={<FaShareAlt />}
//                       onClick={() => doAction(t.topic, "share")}
//                     />
//                     <MenuBtn
//                       label="Rename"
//                       icon={<FaPen />}
//                       onClick={() => doAction(t.topic, "rename")}
//                     />
//                     <MenuBtn
//                       label="Archive"
//                       icon={<FaArchive />}
//                       onClick={() => doAction(t.topic, "archive")}
//                     />
//                     <MenuBtn
//                       label="Delete"
//                       icon={<FaTrash />}
//                       danger
//                       onClick={() => doAction(t.topic, "delete")}
//                     />
//                   </div>
//                 )}
//               </div>
//             );
//           })}
//       </div>

//       {/* New Chat */}
//       <button
//         onClick={() => onNewChat()}
//         className={`mt-1 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm py-2 px-3 rounded-lg shadow-sm transition-colors ${collapsed ? "px-0" : ""
//           }`}
//         title="New Chat"
//       >
//         <FaPlus />
//         {!collapsed && <span>New Research</span>}
//       </button>
//     </aside>
//   );
// }

// function MenuBtn({
//   label,
//   icon,
//   onClick,
//   danger,
// }: {
//   label: string;
//   icon: React.ReactNode;
//   onClick: () => void;
//   danger?: boolean;
// }) {
//   return (
//     <button
//       type="button"
//       className={`w-full text-left px-3 py-2 text-sm flex items-center gap-2 hover:bg-slate-50 ${danger ? "text-rose-600 hover:text-rose-700" : "text-slate-700"
//         }`}
//       onClick={(e) => {
//         e.stopPropagation();
//         onClick();
//       }}
//     >
//       <span className="text-xs">{icon}</span>
//       {label}
//     </button>
//   );
// }

import { useEffect, useMemo, useRef, useState } from "react";
import {
  FaComments,
  FaPlus,
  FaEllipsisV,
  FaShareAlt,
  FaPen,
  FaArchive,
  FaTrash,
  FaChevronLeft,
  FaChevronRight,
  FaDownload,
} from "react-icons/fa";

const API_BASE = "http://127.0.0.1:8000";

type TopicRow = { topic: string; last_at: string; count: number };

interface SidebarProps {
  currentTopic: string | null;
  onOpenTopic: (topic: string) => void;
  onNewChat: () => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  refreshNonce?: number;
}

export default function Sidebar({
  currentTopic,
  onOpenTopic,
  onNewChat,
  collapsed,
  onToggleCollapse,
  refreshNonce,
}: SidebarProps) {
  const [topics, setTopics] = useState<TopicRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [menuOpenFor, setMenuOpenFor] = useState<string | null>(null);
  const menusRef = useRef<Map<string, HTMLDivElement | null>>(new Map());

  const reportIdCache = useMemo(() => new Map<string, number | null>(), []);

  const loadHistory = async () => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/chat-history`, {
        credentials: "include", // ✅ Send cookies
      });
      if (!res.ok) throw new Error("Failed to load history");
      const data: TopicRow[] = await res.json();
      setTopics(data);
    } catch (e: any) {
      setError(e?.message || "Failed to load history");
      setTopics([]);
    }
  };

  // Initial load
  useEffect(() => {
    loadHistory();
  }, []);

  // Refresh when parent bumps the nonce
  useEffect(() => {
    if (typeof refreshNonce === "number") {
      reportIdCache.clear();
      loadHistory();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshNonce]);

  useEffect(() => {
    function handleDocClick(e: MouseEvent) {
      if (!menuOpenFor) return;
      const el = menusRef.current.get(menuOpenFor);
      if (el && !el.contains(e.target as Node)) setMenuOpenFor(null);
    }
    document.addEventListener("click", handleDocClick);
    return () => document.removeEventListener("click", handleDocClick);
  }, [menuOpenFor]);

  async function getReportIdForTopic(topic: string): Promise<number | null> {
    if (reportIdCache.has(topic)) return reportIdCache.get(topic)!;
    try {
      const r = await fetch(
        `${API_BASE}/api/report-by-topic?topic=${encodeURIComponent(topic)}`,
        { credentials: "include" } // ✅ Send cookies
      );
      if (!r.ok) {
        reportIdCache.set(topic, null);
        return null;
      }
      const data = await r.json();
      const id = typeof data?.id === "number" ? data.id : null;
      reportIdCache.set(topic, id);
      return id;
    } catch {
      reportIdCache.set(topic, null);
      return null;
    }
  }

  const fetchChatIds = async (topic: string): Promise<number[]> => {
    try {
      const r = await fetch(
        `${API_BASE}/api/chat-thread?topic=${encodeURIComponent(topic)}`,
        { credentials: "include" } // ✅ Send cookies
      );
      if (!r.ok) return [];
      const rows = (await r.json()) as Array<{ id: number }>;
      return rows.map((m) => m.id);
    } catch {
      return [];
    }
  };

  // File download utilities
  function sanitizeFilename(name: string) {
    return name.replace(/[\\/:*?"<>|]/g, "_").slice(0, 120);
  }
  async function downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    try {
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } finally {
      URL.revokeObjectURL(url);
    }
  }
  async function downloadUrlAs(url: string, filename: string) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error("Failed to fetch file for download");
    const blob = await resp.blob();
    await downloadBlob(blob, filename);
  }

  async function cascadeRename(topic: string, newName: string, rid: number) {
    await fetch(`${API_BASE}/api/history/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        kind: "report",
        id: rid,
        action: "rename",
        value: newName,
      }),
      credentials: "include", // ✅ Send cookies
    });

    const ids = await fetchChatIds(topic);
    for (const id of ids) {
      await fetch(`${API_BASE}/api/history/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind: "chat",
          id,
          action: "rename",
          value: newName,
        }),
        credentials: "include", // ✅ Send cookies
      });
    }
  }

  async function cascadeMark(topic: string, rid: number, action: "archive" | "delete") {
    await fetch(`${API_BASE}/api/history/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind: "report", id: rid, action }),
      credentials: "include", // ✅ Send cookies
    });

    const ids = await fetchChatIds(topic);
    for (const id of ids) {
      await fetch(`${API_BASE}/api/history/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: "chat", id, action }),
        credentials: "include", // ✅ Send cookies
      });
    }
  }

  // Actions
  async function doAction(
    topic: string,
    action: "share" | "rename" | "archive" | "delete" | "download"
  ) {
    try {
      const rid = await getReportIdForTopic(topic);
      if (!rid && action !== "delete" && action !== "archive" && action !== "download") {
        alert("No report found for this topic.");
        return;
      }

      if (action === "download") {
        const resp = await fetch(
          `${API_BASE}/api/report-by-topic?topic=${encodeURIComponent(topic)}`,
          { credentials: "include" } // ✅ Send cookies
        );
        if (!resp.ok) throw new Error("Unable to fetch report for download");
        const data = await resp.json();
        const safe = sanitizeFilename(topic);

        const pdfUrlRaw: string | undefined =
          data?.pdf_url || data?.pdf || data?.pdfPath;
        const reportText: string | undefined =
          data?.report || data?.research || data?.content;

        if (pdfUrlRaw) {
          const pdfUrl =
            pdfUrlRaw.startsWith("http")
              ? pdfUrlRaw
              : `${API_BASE}${pdfUrlRaw.startsWith("/") ? pdfUrlRaw : `/${pdfUrlRaw}`}`;
          await downloadUrlAs(pdfUrl, `${safe}.pdf`);
        } else if (typeof reportText === "string" && reportText.trim()) {
          const mdBlob = new Blob([reportText], {
            type: "text/markdown;charset=utf-8",
          });
          await downloadBlob(mdBlob, `${safe}.md`);
        } else {
          const threadResp = await fetch(
            `${API_BASE}/api/chat-thread?topic=${encodeURIComponent(topic)}`,
            { credentials: "include" } // ✅ Send cookies
          );
          if (!threadResp.ok) throw new Error("Unable to fetch chat thread");
          const thread = await threadResp.json();
          const jsonBlob = new Blob([JSON.stringify(thread, null, 2)], {
            type: "application/json;charset=utf-8",
          });
          await downloadBlob(jsonBlob, `${safe}-thread.json`);
        }

        setMenuOpenFor(null);
        return;
      }

      if (action === "share") {
        const r = await fetch(`${API_BASE}/api/history/action`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ kind: "report", id: rid, action: "share" }),
          credentials: "include", // ✅ Send cookies
        });
        const j = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(j?.error || "Failed to share");
        const full = window.location.origin + (j?.share_url || "");
        try {
          await navigator.clipboard.writeText(full);
          alert("Share link copied:\n" + full);
        } catch {
          prompt("Share link (copy):", full);
        }
        setMenuOpenFor(null);
        return;
      }

      if (action === "rename") {
        const newName = prompt("New topic name:", topic);
        if (!newName || newName.trim() === "" || newName.trim() === topic) {
          setMenuOpenFor(null);
          return;
        }
        await cascadeRename(topic, newName.trim(), rid!);
        reportIdCache.delete(topic);
        setMenuOpenFor(null);
        await loadHistory();
        if (currentTopic === topic) onOpenTopic(newName.trim());
        return;
      }

      if (action === "archive") {
        if (!confirm("Archive this topic (report + chat)?")) {
          setMenuOpenFor(null);
          return;
        }
        if (rid) await cascadeMark(topic, rid, "archive");
        setMenuOpenFor(null);
        await loadHistory();
        if (currentTopic === topic) onNewChat();
        return;
      }

      if (action === "delete") {
        if (!confirm("Delete this topic permanently (report + chat)?")) {
          setMenuOpenFor(null);
          return;
        }
        if (rid) await cascadeMark(topic, rid, "delete");
        setMenuOpenFor(null);
        await loadHistory();
        if (currentTopic === topic) onNewChat();
        return;
      }
    } catch (e: any) {
      alert(e?.message || "Action failed");
    }
  }

  const widthClass = collapsed ? "w-16" : "w-72";

  return (
    <aside
      className={`${widthClass} fixed left-0 top-14 h-[calc(100vh-3.5rem)] bg-gradient-to-br from-blue-200 via-yellow-100 to-red-200 backdrop-blur border-r border-slate-200 text-slate-800 flex flex-col p-3 transition-all duration-200 z-30`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        {!collapsed ? (
          <h2 className="text-sm font-semibold flex items-center gap-2 text-slate-700">
            <FaComments /> History
          </h2>
        ) : (
          <div className="w-6 h-6" aria-hidden />
        )}
        <button
          onClick={onToggleCollapse}
          className="text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-md p-2"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <FaChevronRight /> : <FaChevronLeft />}
        </button>
      </div>

      {/* History list */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {error && !collapsed && (
          <div className="text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded p-2">
            {error}
          </div>
        )}
        {topics === null && !collapsed && (
          <div className="text-xs text-slate-500">Loading…</div>
        )}
        {topics && topics.length === 0 && !collapsed && (
          <div className="text-xs text-slate-500">
            No history yet. Generate a report or ask a question.
          </div>
        )}

        {topics &&
          topics.map((t) => {
            const active = currentTopic === t.topic;
            const isOpen = menuOpenFor === t.topic;
            return (
              <div key={`${t.topic}-${t.last_at}`} className="relative">
                <button
                  onClick={() => onOpenTopic(t.topic)}
                  className={`w-full text-left rounded-lg transition group ${active
                      ? "bg-indigo-100 border border-indigo-200"
                      : "bg-white border border-slate-200 hover:bg-slate-50"
                    } ${collapsed ? "p-2" : "p-3"}`}
                  title={t.topic}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="w-7 h-7 rounded-full bg-indigo-500/90 text-white flex items-center justify-center text-xs font-bold">
                        {t.topic?.[0]?.toUpperCase() || "T"}
                      </div>
                      {!collapsed && (
                        <div className="min-w-0">
                          <div className="text-sm truncate font-medium text-slate-800">
                            {t.topic}
                          </div>
                          <div className="text-[11px] text-slate-500 mt-0.5 truncate">
                            {new Date(t.last_at).toLocaleString()} • {t.count} items
                          </div>
                        </div>
                      )}
                    </div>

                    {!collapsed && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setMenuOpenFor((prev) =>
                            prev === t.topic ? null : t.topic
                          );
                        }}
                        className="opacity-90 hover:opacity-100 text-slate-500 px-2 py-1 rounded-md hover:bg-slate-100"
                        title="More"
                      >
                        <FaEllipsisV />
                      </button>
                    )}
                  </div>
                </button>

                {isOpen && !collapsed && (
                  <div
                    ref={(el) => {
                      menusRef.current.set(t.topic, el);
                    }}
                    className="absolute right-2 top-12 z-30 bg-white border border-slate-200 rounded-lg shadow-lg w-44 py-1"
                  >
                    <MenuBtn
                      label="Download"
                      icon={<FaDownload />}
                      onClick={() => doAction(t.topic, "download")}
                    />
                    <MenuBtn
                      label="Share"
                      icon={<FaShareAlt />}
                      onClick={() => doAction(t.topic, "share")}
                    />
                    <MenuBtn
                      label="Rename"
                      icon={<FaPen />}
                      onClick={() => doAction(t.topic, "rename")}
                    />
                    <MenuBtn
                      label="Archive"
                      icon={<FaArchive />}
                      onClick={() => doAction(t.topic, "archive")}
                    />
                    <MenuBtn
                      label="Delete"
                      icon={<FaTrash />}
                      danger
                      onClick={() => doAction(t.topic, "delete")}
                    />
                  </div>
                )}
              </div>
            );
          })}
      </div>

      <button
        onClick={() => onNewChat()}
        className={`mt-1 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm py-2 px-3 rounded-lg shadow-sm transition-colors ${collapsed ? "px-0" : ""
          }`}
        title="New Chat"
      >
        <FaPlus />
        {!collapsed && <span>New Research</span>}
      </button>
    </aside>
  );
}

function MenuBtn({
  label,
  icon,
  onClick,
  danger,
}: {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      className={`w-full text-left px-3 py-2 text-sm flex items-center gap-2 hover:bg-slate-50 ${danger ? "text-rose-600 hover:text-rose-700" : "text-slate-700"
        }`}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
    >
      <span className="text-xs">{icon}</span>
      {label}
    </button>
  );
}
