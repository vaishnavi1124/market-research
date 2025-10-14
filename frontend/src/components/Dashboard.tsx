// // frontend/src/components/Dashboard.tsx

import React, { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  FaCogs,
  FaDownload,
  FaExclamationTriangle,
  FaFileAlt,
  FaChartLine,
  FaSearch,
  FaPlus,
  FaTimes,
  FaFileUpload,
  FaTrash,
} from "react-icons/fa";
import { BarLoader } from "react-spinners";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

const API_BASE =
  (import.meta as any)?.env?.VITE_API_URL || "http://127.0.0.1:8000";

/** ===== Props coming from App so Dashboard can react to Sidebar selections ===== */
interface DashboardProps {
  selectedTopic: string | null;
  newChatNonce: number;
  onOpenedTopic: (topic: string) => void;
  onHistoryChange: () => void;
  setChatbotExternalSuggestions?: (sugs: string[] | null) => void;
  setChatbotExternalIntro?: (text: string | null) => void;
}

interface ReportData {
  report: string;
  pdf_url?: string | null;
  research?: string;
  created_at?: string | null;
  suggestions?: unknown;
}

/** Example graph data for fenced code -> "graph" demo */
const sampleGraphData = [
  { name: "2015", value: 200 },
  { name: "2020", value: 400 },
  { name: "2025", value: 800 },
];

import type { Components } from "react-markdown";

/** ==== Pretty Markdown renderer with a small graph demo ==== */
const MarkdownRenderer: React.FC<{ content: string }> = ({ content }) => {
  const components: Components = {
    a: ({ ...props }) => (
      <a
        {...props}
        className="text-indigo-600 underline hover:text-indigo-800 transition-colors"
        target="_blank"
        rel="noreferrer"
      />
    ),
    h2: ({ ...props }) => (
      <h2
        className="text-xl font-bold text-indigo-700 mt-8 mb-4 border-b border-indigo-200 pb-1"
        {...props}
      />
    ),
    h3: ({ ...props }) => (
      <h3 className="text-lg font-semibold text-purple-700 mt-6 mb-3" {...props} />
    ),
    h4: ({ ...props }) => (
      <h4 className="text-base font-semibold text-gray-800 mt-4 mb-2" {...props} />
    ),
    p: ({ ...props }) => <p className="mb-3 leading-relaxed text-gray-700" {...props} />,
    ul: ({ ...props }) => (
      <ul className="list-disc pl-6 mb-3 space-y-1.5 text-gray-700" {...props} />
    ),
    li: ({ ...props }) => <li className="leading-snug" {...props} />,
    ol: ({ ...props }) => (
      <ol className="list-decimal pl-6 mb-3 space-y-1.5 text-gray-700" {...props} />
    ),
    blockquote: ({ ...props }) => (
      <blockquote
        className="border-l-4 border-indigo-400 bg-indigo-50/60 italic pl-4 pr-2 py-2 rounded-r-lg my-4 text-gray-700"
        {...props}
      />
    ),
    table: ({ ...props }) => (
      <div className="overflow-x-auto my-5 rounded-lg border border-gray-200/60 shadow-sm">
        <table className="table-auto border-collapse w-full text-sm bg-white/70 backdrop-blur-sm">
          {props.children}
        </table>
      </div>
    ),
    th: ({ ...props }) => (
      <th className="border border-gray-200/60 bg-gray-100/70 px-4 py-2 text-left font-semibold text-gray-700 align-top">
        {props.children}
      </th>
    ),
    
    td: ({ ...props }) => (
      <td className="border border-gray-200/60 px-4 py-2 text-gray-700 align-top">
        {props.children}
      </td>
    ),
    
    
    code: ({
      inline,
      children,
    }: React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
      inline?: boolean;
    }) => {
      const txt = String(children).trim();
      if (!inline && txt.toLowerCase().includes("graph")) {
        return (
          <div className="bg-white/80 backdrop-blur-md p-4 rounded-lg border border-gray-200/60 my-5">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={sampleGraphData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="value" strokeWidth={3} dot />
              </LineChart>
            </ResponsiveContainer>
          </div>
        );
      }
      return inline ? (
        <code className="bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded text-[13px] font-mono">
          {txt}
        </code>
      ) : (
        <pre className="bg-slate-900/90 text-gray-100 p-4 rounded-lg overflow-x-auto my-4 shadow-inner">
          <code className="font-mono text-sm">{txt}</code>
        </pre>
      );
    },
  };

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeRaw]}
      skipHtml={false}
      components={components}
    >
      {content}
    </ReactMarkdown>
  );
};

/* ==================== Downloads helpers (unchanged) ==================== */
function sanitizeFilename(name: string) {
  return (name || "report").replace(/[\\/:*?"<>|]/g, "_").slice(0, 120);
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
function basename(pathOrName: string) {
  if (!pathOrName) return pathOrName;
  try {
    const parts = pathOrName.split(/[/\\]/);
    return parts[parts.length - 1] || pathOrName;
  } catch {
    return pathOrName;
  }
}
async function downloadViaBackend(filename: string) {
  const url = `${API_BASE}/download-pdf/${encodeURIComponent(filename)}`;
  const resp = await fetch(url, { credentials: "include" });
  if (!resp.ok) {
    throw new Error("Failed to download PDF from server");
  }
  const blob = await resp.blob();
  await downloadBlob(blob, filename);
}
function normalizePdfUrl(pdfUrl: string) {
  if (!pdfUrl) return "";
  return pdfUrl.startsWith("http")
    ? pdfUrl
    : `${API_BASE}${pdfUrl.startsWith("/") ? pdfUrl : `/${pdfUrl}`}`;
}
async function downloadUrlAs(url: string, filename: string) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error("Failed to fetch file for download");
  const blob = await resp.blob();
  await downloadBlob(blob, filename);
}
function topicToPdfFilename(topic: string) {
  const base = topic.replace(/ /g, "_").replace(/\//g, "_").replace(/:/g, "_").slice(0, 50);
  return `${base}_writer_report.pdf`;
}
async function downloadReport({
  topic,
  reportText,
  pdfUrl,
}: {
  topic: string;
  reportText?: string | null;
  pdfUrl?: string | null;
}) {
  const safe = sanitizeFilename(topic);
  const candidateFile = pdfUrl?.trim()
    ? basename(pdfUrl)
    : topicToPdfFilename(topic);

  try {
    await downloadViaBackend(candidateFile);
    return;
  } catch {
    if (pdfUrl && pdfUrl.trim()) {
      try {
        await downloadUrlAs(normalizePdfUrl(pdfUrl), `${safe}.pdf`);
        return;
      } catch {
        // continue
      }
    }
  }

  if (reportText && reportText.trim()) {
    const mdBlob = new Blob([reportText], { type: "text/markdown;charset=utf-8" });
    await downloadBlob(mdBlob, `${safe}.md`);
    return;
  }

  const r = await fetch(
    `${API_BASE}/api/chat-thread?topic=${encodeURIComponent(topic)}`
  );
  if (!r.ok) throw new Error("Unable to fetch chat thread");
  const thread = await r.json();
  const jsonBlob = new Blob([JSON.stringify(thread, null, 2)], {
    type: "application/json;charset=utf-8",
  });
  await downloadBlob(jsonBlob, `${safe}-thread.json`);
}

/* ============== Suggestions normalizer (unchanged) ============== */
function coerceSuggestions(raw: unknown): string[] {
  if (!raw) return [];
  try {
    if (typeof raw === "string" && /^[\s]*[\[{]/.test(raw)) {
      const parsed = JSON.parse(raw);
      return coerceSuggestions(parsed);
    }
  } catch { }
  if (Array.isArray(raw)) {
    const out: string[] = [];
    for (const it of raw) {
      if (typeof it === "string" && it.trim()) out.push(it.trim());
      else if (it && typeof it === "object") {
        const anyIt = it as any;
        const cand =
          anyIt.question ??
          anyIt.text ??
          anyIt.q ??
          (typeof anyIt.toString === "function" ? anyIt.toString() : "");
        if (typeof cand === "string" && cand.trim()) out.push(cand.trim());
      }
    }
    return out;
  }
  if (raw && typeof raw === "object") {
    const anyObj = raw as any;
    if (Array.isArray(anyObj.suggestions)) return coerceSuggestions(anyObj.suggestions);
  }
  if (typeof raw === "string") return raw.trim() ? [raw.trim()] : [];
  return [];
}

/* ==================== NEW: Dynamic sectors & categories ==================== */
type Sector = { sector_id: number; sector_name: string };
type Category = { category_id: number; category_name: string };

const ADD_OPTION = "__add__";

const Dashboard: React.FC<DashboardProps> = ({
  selectedTopic,
  newChatNonce,
  onOpenedTopic,
  onHistoryChange,
  setChatbotExternalSuggestions,
  setChatbotExternalIntro,
}) => {
  // list of locally created reports in this session
  const [reports, setReports] = useState<ReactNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [progressMessages, setProgressMessages] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // report fetched by clicking a topic in the Sidebar
  const [loadedTopic, setLoadedTopic] = useState<string | null>(null);
  const [loadedReport, setLoadedReport] = useState<string | null>(null);
  const [loadedPdfUrl, setLoadedPdfUrl] = useState<string | null>(null);
  const [loadedCreatedAt, setLoadedCreatedAt] = useState<string | null>(null);
  const [loadingTopic, setLoadingTopic] = useState(false);

  // suggestions & inline chatbot follow-ups for the loaded topic
  const [loadedSuggestions, setLoadedSuggestions] = useState<string[] | null>(null);
  const [followups, setFollowups] = useState<
    Array<{ q: string; a?: string; err?: string; loading?: boolean }>
  >([]);

  // keep a current topic ref so chips work even before state settles
  const currentTopicRef = useRef<string | null>(null);
  useEffect(() => {
    currentTopicRef.current = loadedTopic;
  }, [loadedTopic]);

  /** === WS progress === */
  const wsUrl = useMemo(
    () => API_BASE.replace(/^http/, "ws") + "/ws/progress",
    []
  );
  const initWebSocket = () => {
    try {
      const ws = new WebSocket(wsUrl);
      ws.onopen = () => console.log("✅ WS connected");
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setProgressMessages((prev) => [...prev, data.message]);
        } catch { }
      };
      ws.onclose = () => console.log("❌ WS closed");
      ws.onerror = () => {
        setProgressMessages((prev) => [
          ...prev,
          "Error: Unable to track backend progress",
        ]);
      };
      wsRef.current = ws;
    } catch (e) {
      console.warn("WS init failed", e);
    }
  };

  /* --------- NEW STATE: sectors & categories --------- */
  const [sectors, setSectors] = useState<Sector[]>([]);
  const [sectorsLoading, setSectorsLoading] = useState<boolean>(false);
  const [sectorValue, setSectorValue] = useState<string>("");
  const [sectorModeAdd, setSectorModeAdd] = useState<boolean>(false);
  const [newSectorName, setNewSectorName] = useState<string>("");

  const [categories, setCategories] = useState<Category[]>([]);
  const [categoriesLoading, setCategoriesLoading] = useState<boolean>(false);
  const [categoryValue, setCategoryValue] = useState<string>("");
  const [categoryModeAdd, setCategoryModeAdd] = useState<boolean>(false);
  const [newCategoryName, setNewCategoryName] = useState<string>("");

  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  /* Fetch sectors on mount */
  const fetchSectors = async () => {
    setSectorsLoading(true);
    try {
      const r = await fetch(`${API_BASE}/api/sectors`, { credentials: "include" });
      const data: Sector[] = r.ok ? await r.json() : [];
      setSectors(data || []);
    } catch {
      setSectors([]);
    } finally {
      setSectorsLoading(false);
    }
  };

  /* Fetch categories when sector changes */
  const fetchCategories = async (sectorName: string) => {
    if (!sectorName) {
      setCategories([]);
      return;
    }
    setCategoriesLoading(true);
    try {
      const r = await fetch(
        `${API_BASE}/api/sectors/${encodeURIComponent(sectorName)}/categories`,
        { credentials: "include" }
      );
      const data: Category[] = r.ok ? await r.json() : [];
      setCategories(data || []);
    } catch {
      setCategories([]);
    } finally {
      setCategoriesLoading(false);
    }
  };

  /* Add new sector (inline) */
  const addSector = async (name: string) => {
    const body = JSON.stringify({ sector_name: name });
    const r = await fetch(`${API_BASE}/api/sectors`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      credentials: "include",
    });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.error || "Failed to add sector");
    }
    await fetchSectors();
    setSectorValue(name);
    setSectorModeAdd(false);
    setNewSectorName("");
    await fetchCategories(name);
  };

  /* Add new category (inline) */
  const addCategory = async (sectorName: string, catName: string) => {
    const body = JSON.stringify({ category_name: catName });
    const r = await fetch(
      `${API_BASE}/api/sectors/${encodeURIComponent(sectorName)}/categories`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        credentials: "include",
      }
    );
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.error || "Failed to add category");
    }
    await fetchCategories(sectorName);
    setCategoryValue(catName);
    setCategoryModeAdd(false);
    setNewCategoryName("");
  };

  useEffect(() => {
    fetchSectors();
  }, []);

  /** === Load a report when a topic is selected from Sidebar === */
  useEffect(() => {
    let ignore = false;
    async function loadByTopic(topic: string) {
      setLoadingTopic(true);
      setLoadedReport(null);
      setLoadedPdfUrl(null);
      setLoadedTopic(topic);
      currentTopicRef.current = topic;
      setLoadedSuggestions(null);
      setFollowups([]);
      try {
        const r = await fetch(
          `${API_BASE}/api/report-by-topic?topic=${encodeURIComponent(topic)}`,
          { credentials: "include" }
        );
        if (!r.ok) {
          const j = await r.json().catch(() => ({}));
          throw new Error(j.error || "Report not found");
        }
        const data: ReportData = await r.json();
        if (!ignore) {
          const body = data.research || data.report || "";
          setLoadedReport(body);
          setLoadedPdfUrl(data.pdf_url || null);
          setLoadedCreatedAt(data.created_at || null);

          const sugs = coerceSuggestions(data.suggestions);
          if (sugs.length) {
            setLoadedSuggestions(sugs);
            setChatbotExternalSuggestions?.(sugs);
            setChatbotExternalIntro?.("Here are some suggested follow-ups for this report:");
          } else {
            setLoadedSuggestions(null);
            setChatbotExternalSuggestions?.(null);
            setChatbotExternalIntro?.(null);
          }
        }
      } catch (e: any) {
        if (!ignore) {
          setLoadedReport(`> ⚠️ ${e?.message || "Failed to load report"}`);
          setLoadedPdfUrl(null);
          setLoadedCreatedAt(null);
          setLoadedSuggestions(null);
          setFollowups([]);
          setChatbotExternalSuggestions?.(null);
          setChatbotExternalIntro?.(null);
        }
      } finally {
        if (!ignore) setLoadingTopic(false);
      }
    }

    if (selectedTopic) {
      loadByTopic(selectedTopic);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else {
      // new chat => clear the loaded view
      setLoadedTopic(null);
      currentTopicRef.current = null;
      setLoadedReport(null);
      setLoadedPdfUrl(null);
      setLoadedCreatedAt(null);
      setLoadedSuggestions(null);
      setFollowups([]);
      setLoadingTopic(false);
      setChatbotExternalSuggestions?.(null);
      setChatbotExternalIntro?.(null);
      setSelectedFile(null); // <-- Clear file on new chat
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }

    return () => {
      ignore = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTopic, newChatNonce]);

  /** === Handle Report Generation from the form === */
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setProgressMessages(["Starting backend process…"]);

    const formData = new FormData(e.currentTarget);

    const resolvedSector =
      sectorModeAdd ? newSectorName.trim() : sectorValue.trim();
    const resolvedCategory =
      categoryModeAdd ? newCategoryName.trim() : categoryValue.trim();

    if (!resolvedSector) {
      setLoading(false);
      alert("Please select or add a sector.");
      return;
    }
    if (!resolvedCategory) {
      setLoading(false);
      alert("Please select or add a product category.");
      return;
    }

    formData.set("sector", resolvedSector);
    formData.set("category", resolvedCategory);

    const researchType = String(formData.get("research_type") || "");
    const goals = String(formData.get("goals") || "");
    const clientName = String(formData.get("client_name") || "");
    const briefDetails = String(formData.get("brief_details") || "");

    const scopeValues: string[] = [];
    (formData.getAll("scope") as string[]).forEach((v) => scopeValues.push(v));
    formData.set("scope", scopeValues.join(","));

    initWebSocket();

    try {
      if (sectorModeAdd && resolvedSector) await addSector(resolvedSector);
      if (categoryModeAdd && resolvedCategory && resolvedSector)
        await addCategory(resolvedSector, resolvedCategory);

      const response = await fetch(`${API_BASE}/generate-report`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (wsRef.current) wsRef.current.close();
      if (!response.ok) {
        const j = await response.json().catch(() => ({}));
        throw new Error(j.error || "Failed to generate report");
      }

      const data: ReportData = await response.json();
      const title = `${resolvedSector} - ${researchType}`;
      const summary = `Client: ${clientName || "N/A"}; Goals: ${goals}; Scope: ${scopeValues.join(", ") || "N/A"}; Brief: ${briefDetails}`;

      const sugs = coerceSuggestions(data.suggestions);

      const onDownload = async () => {
        try {
          await downloadReport({
            topic: title,
            reportText: data.report,
            pdfUrl: data.pdf_url ?? null,
          });
        } catch (err: any) {
          alert(err?.message || "Download failed");
        }
      };

      currentTopicRef.current = title;

      const entry = (
        <div
          className="bg-white/60 backdrop-blur-md p-6 md:p-8 rounded-xl border border-gray-200/60 shadow-sm transition-all duration-300 space-y-5"
          key={`${title}-${Date.now()}`}
        >
          <div className="flex items-start justify-between">
            <h3 className="flex items-center gap-3 text-xl font-bold text-gray-800">
              <span className="p-2 bg-indigo-50 border border-indigo-100 rounded-lg">
                <FaFileAlt className="text-indigo-600" size={20} />
              </span>
              {title}
            </h3>
            <div className="flex items-center gap-2 text-xs text-gray-700">
              <FaChartLine />
              Generated Report
            </div>
          </div>

          <div className="rounded-lg p-4 border-l-4 border-indigo-500 bg-white/70">
            <p className="text-sm text-gray-700 leading-relaxed">
              <span className="font-semibold text-indigo-700">Request Summary:</span>{" "}
              {summary}
            </p>
          </div>

          <div className="rounded-lg p-3 text-sm text-gray-700 space-y-1 bg-white/60 border border-gray-200/60">
            {progressMessages.map((msg, idx) => (
              <p key={idx}>• {msg}</p>
            ))}
          </div>

          <div className="prose prose-sm max-w-none text-gray-700">
            <MarkdownRenderer content={data.report} />
          </div>

          {sugs.length > 0 && (
            <div className="mt-2">
              <div className="text-xs font-semibold text-gray-600 mb-2">
                Suggested follow-ups
              </div>
              <div className="flex flex-wrap gap-2">
                {sugs.map((sug, i) => (
                  <button
                    key={`${title}-card-sug-${i}`}
                    onClick={() => askChatbot(sug, title)}
                    className="px-3 py-1.5 text-xs rounded-full border border-indigo-200 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 transition-colors"
                    title="Ask this follow-up"
                  >
                    {sug}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end pt-4 border-t border-gray-200/60">
            <button
              type="button"
              onClick={onDownload}
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 shadow-sm transition-all"
              title="Download report"
            >
              <FaDownload /> Download Report
            </button>
          </div>
        </div>
      );

      setReports((prev) => (!loadedTopic ? [entry, ...prev] : prev));

      onOpenedTopic(title);
      onHistoryChange();

      setLoadedTopic(title);
      setLoadedReport(data.report || "");
      setLoadedPdfUrl(data.pdf_url || null);
      setLoadedCreatedAt(new Date().toISOString());

      setLoadedSuggestions(sugs.length ? sugs : null);
      setFollowups([]);
      setChatbotExternalSuggestions?.(sugs.length ? sugs : null);
      setChatbotExternalIntro?.(
        sugs.length ? "Here are some suggested follow-ups for this report:" : null
      );

      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err: any) {
      const errorMessage = err?.message || "An unexpected error occurred";
      setReports((prev) => [
        <div
          key={`err-${Date.now()}`}
          className="bg-red-50/80 backdrop-blur-md border border-red-200/80 text-red-700 px-6 py-4 rounded-xl flex items-center gap-3 shadow-sm"
        >
          <div className="p-2 bg-red-100 rounded-lg">
            <FaExclamationTriangle className="text-red-600" />
          </div>
          <div>
            <p className="font-semibold">Error generating report</p>
            <p className="text-sm text-red-700">{errorMessage}</p>
          </div>
        </div>,
        ...prev,
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadLoaded = async () => {
    if (!loadedTopic) return;
    try {
      await downloadReport({
        topic: loadedTopic,
        reportText: loadedReport || "",
        pdfUrl: loadedPdfUrl || undefined,
      });
    } catch (err: any) {
      alert(err?.message || "Download failed");
    }
  };

  const askChatbot = async (q: string, explicitTopic?: string) => {
    const effTopic = explicitTopic || loadedTopic || currentTopicRef.current;
    if (!effTopic || !q.trim()) {
      console.warn("No effective topic for chatbot query:", { q, loadedTopic, explicitTopic });
      return;
    }

    setFollowups((prev) => [...prev, { q, loading: true }]);

    try {
      const params = new URLSearchParams({ query: q, topic: effTopic });
      const resp = await fetch(`${API_BASE}/chatbot`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: params,
        credentials: "include",
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || "Chatbot error");

      const answer = (data.response ?? data.answer ?? "").toString();

      setFollowups((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        copy[copy.length - 1] = { ...last, a: answer, loading: false };
        return copy;
      });

      const fresh = coerceSuggestions((data as any).suggestions);
      if (fresh.length) {
        const mergedSet = new Set([...(loadedSuggestions || []), ...fresh]);
        const merged = Array.from(mergedSet);
        setLoadedSuggestions(merged);
        setChatbotExternalSuggestions?.(merged);
        setChatbotExternalIntro?.("More follow-up questions you can ask:");
      }

      onHistoryChange();
    } catch (err: any) {
      setFollowups((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        copy[copy.length - 1] = {
          ...last,
          err: err?.message || "Something went wrong",
          loading: false,
        };
        return copy;
      });
    }
  };

  return (
    <div className="mx-auto px-2 md:px-3 space-y-2">
      {/* Form */}
      <div className="bg-transparent backdrop-blur-md rounded-2xl shadow-sm border border-gray-200/60 overflow-hidden">
        <div className="bg-gradient-to-r from-indigo-500 to-purple-600 px-4 py-1">
          <h4 className="text-xs font-mono text-white flex items-center gap-2 tracking-wide">
            <FaSearch /> Research Configuration
          </h4>
          <p className="text-indigo-100 text-[15px] leading-tight">
            Configure your market research parameters
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {/* top row */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Sector (dynamic) */}
            <div className="space-y-1">
              <label className="block text-sm font-semibold text-gray-700">
                Research Sector
              </label>

              {!sectorModeAdd ? (
                <div className="flex gap-2">
                  <select
                    value={sectorValue}
                    onChange={async (e) => {
                      const val = e.target.value;
                      if (val === ADD_OPTION) {
                        setSectorModeAdd(true);
                        return;
                      }
                      setSectorValue(val);
                      setCategoryValue("");
                      setCategoryModeAdd(false);
                      setNewCategoryName("");
                      await fetchCategories(val);
                    }}
                    className="w-full border border-gray-300 rounded-xl px-2 py-2 bg-white/80 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-700"
                    required
                  >
                    <option value="">Select your sector</option>
                    {sectors.map((s) => (
                      <option key={s.sector_id} value={s.sector_name}>
                        {s.sector_name}
                      </option>
                    ))}
                    <option value={ADD_OPTION}>➕ Add new sector…</option>
                  </select>
                  {sectorsLoading && (
                    <span className="text-xs text-gray-500 self-center">Loading…</span>
                  )}
                </div>
              ) : (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newSectorName}
                    onChange={(e) => setNewSectorName(e.target.value)}
                    placeholder="Enter new sector"
                    className="w-full border border-gray-300 rounded-xl px-2 py-2 bg-white/80 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-700"
                    autoFocus
                    required
                  />
                  <button
                    type="button"
                    onClick={async () => {
                      const name = newSectorName.trim();
                      if (!name) return;
                      try {
                        await addSector(name);
                      } catch (e: any) {
                        alert(e?.message || "Failed to add sector");
                      }
                    }}
                    className="px-3 rounded-xl bg-green-600 text-white hover:bg-green-700"
                    title="Add sector"
                  >
                    <FaPlus />
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setSectorModeAdd(false);
                      setNewSectorName("");
                    }}
                    className="px-3 rounded-xl bg-gray-200 text-gray-700 hover:bg-gray-300"
                    title="Cancel"
                  >
                    <FaTimes />
                  </button>
                </div>
              )}
            </div>

            {/* Product Category (dynamic by sector) */}
            <div className="space-y-1">
              <label className="block text-sm font-semibold text-gray-700">
                Product Category
              </label>

              {!categoryModeAdd ? (
                <div className="flex gap-2">
                  <select
                    value={categoryValue}
                    onChange={(e) => {
                      const val = e.target.value;
                      if (val === ADD_OPTION) {
                        setCategoryModeAdd(true);
                        return;
                      }
                      setCategoryValue(val);
                    }}
                    disabled={!sectorValue && !sectorModeAdd}
                    className="w-full border border-gray-300 rounded-xl px-2 py-2 bg-white/80 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-700 disabled:bg-gray-100"
                    required
                    name="category"
                  >
                    <option value="">
                      {sectorValue || sectorModeAdd
                        ? "Select product category"
                        : "Select sector first"}
                    </option>
                    {categories.map((c) => (
                      <option key={c.category_id} value={c.category_name}>
                        {c.category_name}
                      </option>
                    ))}
                    {(sectorValue || sectorModeAdd) && (
                      <option value={ADD_OPTION}>➕ Add new category…</option>
                    )}
                  </select>
                  {categoriesLoading && (
                    <span className="text-xs text-gray-500 self-center">Loading…</span>
                  )}
                </div>
              ) : (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newCategoryName}
                    onChange={(e) => setNewCategoryName(e.target.value)}
                    placeholder="Enter new category"
                    className="w-full border border-gray-300 rounded-xl px-2 py-2 bg-white/80 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-700"
                    autoFocus
                    required
                  />
                  <button
                    type="button"
                    onClick={async () => {
                      const cat = newCategoryName.trim();
                      const sec =
                        sectorModeAdd ? newSectorName.trim() : sectorValue.trim();
                      if (!sec) {
                        alert("Please select/add a sector first.");
                        return;
                      }
                      if (!cat) return;
                      try {
                        if (sectorModeAdd && sec) await addSector(sec);
                        await addCategory(sec, cat);
                      } catch (e: any) {
                        alert(e?.message || "Failed to add category");
                      }
                    }}
                    className="px-3 rounded-xl bg-green-600 text-white hover:bg-green-700"
                    title="Add category"
                  >
                    <FaPlus />
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setCategoryModeAdd(false);
                      setNewCategoryName("");
                    }}
                    className="px-3 rounded-xl bg-gray-200 text-gray-700 hover:bg-gray-300"
                    title="Cancel"
                  >
                    <FaTimes />
                  </button>
                </div>
              )}

              {(sectorValue && !categoriesLoading && categories.length === 0 && !categoryModeAdd) && (
                <div className="text-xs text-gray-500">
                  No categories yet — click “Add new category…” to create one.
                </div>
              )}
            </div>

            {/* Research Type */}
            <div className="space-y-1">
              <label className="block text-sm font-semibold text-gray-700">Research Type</label>
              <select
                name="research_type"
                required
                className="w-full border border-gray-300 rounded-xl px-2 py-2 bg-white/80 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-700"
              >
                <option value="">Choose research type</option>
                <option>Market Opportunity Analysis</option>
                <option>Competitor Benchmarking</option>
                <option>Customer Segmentation</option>
                <option>Pricing Strategy</option>
                <option>Brand Health Monitoring</option>
                <option>Trends & Forecasting</option>
                <option>Go-To-Market Plan</option>
              </select>
            </div>
            {/* Business Goals */}
            <div className="space-y-1">
              <label className="block text-sm font-semibold text-gray-700">Business Goals</label>
              <select
                name="goals"
                required
                className="w-full border border-gray-300 rounded-xl px-2 py-2 bg-white/80 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-700"
              >
                <option value="">Select your goals</option>
                <option>New Product Launch</option>
                <option>Entry to New Market</option>
                <option>Expansion of Existing Services</option>
                <option>Partnership Strategy</option>
              </select>
            </div>
            {/* Client Name */}
            <div className="space-y-1">
              <label className="block text-sm font-semibold text-gray-700">Client Name</label>
              <input
                type="text"
                name="client_name"
                placeholder="Enter client's name"
                className="w-full border border-gray-300 rounded-xl px-2 py-2 bg-white/80 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-700"
              />
            </div>

            {/* ==================== MOVED PDF UPLOAD SECTION ==================== */}
            <div className="space-y-1">
              <label className="block text-sm font-semibold text-gray-700">
                Upload PDF (Optional)
              </label>
              <div>
                <div className="flex items-center gap-3">
                  <label className="cursor-pointer inline-flex items-center gap-2 px-4 py-2 text-sm bg-white border border-gray-300 rounded-xl hover:bg-gray-50 transition-colors">
                    <FaFileUpload className="text-gray-500" />
                    <span>{selectedFile ? "Change file" : "Choose a PDF"}</span>
                    <input
                      type="file"
                      name="pdf_file"
                      className="hidden"
                      accept="application/pdf"
                      ref={fileInputRef}
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        setSelectedFile(file || null);
                      }}
                    />
                  </label>
                </div>
                {selectedFile && (
                  <div className="mt-2 flex items-center gap-2 text-sm text-gray-600 bg-gray-100/80 border border-gray-200/60 px-3 py-1.5 rounded-lg">
                    <FaFileAlt className="text-gray-500 flex-shrink-0" />
                    <span className="truncate max-w-[200px] sm:max-w-xs" title={selectedFile.name}>
                      {selectedFile.name}
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedFile(null);
                        if (fileInputRef.current) {
                           fileInputRef.current.value = "";
                        }
                      }}
                      className="text-gray-500 hover:text-red-600 ml-auto"
                      title="Remove file"
                    >
                      <FaTrash />
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Scope */}
          <div className="space-y-1">
            <label className="block text-sm font-semibold text-gray-700">Geographic Scope</label>
            <div className="bg-gray-50/70 rounded-xl p-2 border border-gray-200/60">
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
                {["India", "APAC", "Europe", "North America", "Middle East", "Africa", "Latin America"].map(
                  (region) => (
                    <label
                      key={region}
                      className="flex items-center gap-3 text-sm text-gray-700 cursor-pointer hover:text-indigo-600"
                    >
                      <input
                        type="checkbox"
                        name="scope"
                        value={region}
                        className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                      />
                      <span className="font-medium">{region}</span>
                    </label>
                  )
                )}
              </div>
            </div>
          </div>

          {/* Brief */}
          <div className="space-y-1">
            <label className="block text-sm font-semibold text-gray-700">Research Requirements</label>
            <textarea
              name="brief_details"
              rows={2}
              required
              placeholder="Describe your research needs, key questions, audience, timeline, etc."
              className="w-full border border-gray-300 rounded-xl px-2 py-2 bg-white/80 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-700 resize-none"
            />
          </div>

          {/* Submit */}
          <div className="flex items-center justify-between pt-2 border-t border-gray-200/60">
            <div className="text-sm text-gray-500">
              Ensure all required fields are completed.
            </div>
            <button
              type="submit"
              disabled={loading}
              className={`flex items-center gap-3 px-4 py-2 rounded-xl text-white font-semibold transition-all ${loading
                  ? "bg-gray-400 cursor-not-allowed"
                  : "bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-600"
                }`}
            >
              <FaCogs className={loading ? "animate-spin" : ""} />
              {loading ? "Generating Report..." : "Generate Research Report"}
            </button>
          </div>

          {loading && (
            <div className="flex flex-col items-center space-y-2 pt-2">
              <div className="relative w-[300px] h-[3px] rounded-full overflow-hidden bg-gradient-to-r from-blue-600 via-indigo-500 to-teal-400 animate-gradient-x">
                <div className="absolute inset-0 flex items-center justify-center">
                  <BarLoader
                    width={300}
                    height={6}
                    color="#ffffff"
                    speedMultiplier={0.8}
                  />
                </div>
              </div>
              <p className="text-sm bg-gradient-to-r from-purple-600 via-pink-500 to-orange-400 bg-clip-text text-transparent animate-pulse">
                Analyzing market data and generating insights...
              </p>
              <div className="rounded-lg p-2 w-full max-h-20 overflow-y-auto text-xs text-green-900  bg-transparent">
                {progressMessages.map((msg, idx) => (
                  <p key={idx}>• {msg}</p>
                ))}
              </div>
            </div>
          )}
        </form>
      </div>

      {/* Selected topic viewer (from Sidebar) */}
      {loadedTopic && (
        <div className="bg-transparent p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
              <FaFileAlt className="text-indigo-600" /> {loadedTopic}
            </h3>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleDownloadLoaded}
                className="inline-flex items-center gap-2 px-3 py-1.5 text-xs bg-indigo-600 text-white rounded-md hover:bg-indigo-700 shadow-sm transition-all"
                title="Download report"
              >
                <FaDownload /> Download
              </button>
              {loadedCreatedAt && (
                <div className="text-xs text-gray-500">
                  Created: {new Date(loadedCreatedAt).toLocaleString()}
              </div>
              )}
            </div>
          </div>

          {loadingTopic ? (
            <div className="py-8 text-center text-sm text-gray-600">Loading report…</div>
          ) : (
            <>
              <div className="prose prose-sm max-w-none text-gray-700">
                <MarkdownRenderer content={loadedReport || "_(No report content found)_"} />
              </div>

              {loadedSuggestions && loadedSuggestions.length > 0 && (
                <div className="mt-4 pt-3 border-t border-gray-200/60">
                  <div className="text-xs font-semibold text-gray-600 mb-2">
                    Suggested follow-ups
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {loadedSuggestions.map((sug, i) => (
                      <button
                        key={`${loadedTopic}-sug-${i}`}
                        onClick={() => askChatbot(sug)}
                        className="px-3 py-1.5 text-xs rounded-full border border-indigo-200 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 transition-colors"
                        title="Ask this follow-up"
                      >
                        {sug}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {followups.length > 0 && (
                <div className="mt-5 space-y-3">
                  {followups.map((f, idx) => (
                    <div key={`fu-${idx}`} className="space-y-1">
                      <div className="flex justify-end">
                        <div className="inline-block bg-slate-800 text-white rounded-2xl rounded-tr-md px-3 py-2 text-xs max-w-[85%]">
                          {f.q}
                        </div>
                      </div>
                      <div className="flex justify-start">
                        <div className="inline-block bg-white/80 border border-gray-200/80 text-gray-800 rounded-2xl px-3 py-2 text-sm max-w-[85%]">
                          {f.loading && <span className="text-gray-500">💭 thinking…</span>}
                          {!f.loading && f.err && (
                            <span className="text-red-600">❌ {f.err}</span>
                          )}
                          {!f.loading && f.a && (
                            <div className="prose prose-sm max-w-none text-gray-800">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {f.a}
                              </ReactMarkdown>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Session Reports List */}
      {!loadedTopic && reports.length > 0 && (
        <div className="space-y-4">
          <div className="text-center">
            <h2 className="text-xl font-bold text-gray-800 mb-1">
              Generated Research Reports (this session)
            </h2>
            <p className="text-gray-600 text-sm">
              Your comprehensive market intelligence reports
            </p>
          </div>
          <div className="space-y-5">{reports}</div>
        </div>
      )}

      {/* Empty State */}
      {reports.length === 0 && !loadedTopic && !loading && (
        <div className="text-center py-12">
          <div className="p-3 bg-white/70 border rounded-full w-20 h-20 mx-auto mb-3 flex items-center justify-center">
            <FaFileAlt className="text-gray-400" size={28} />
          </div>
          <h3 className="text-lg font-semibold text-gray-600 mb-1">
            No Reports Generated Yet
          </h3>
          <p className="text-gray-500 text-sm">
            Fill out the form above to generate your first market research report,
            or select a topic from the left sidebar.
          </p>
        </div>
      )}
    </div>
  );
};

export default Dashboard;