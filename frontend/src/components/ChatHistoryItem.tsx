// frontend\src\components\ChatHistoryItem.tsx
import React, { useEffect, useRef, useState } from "react";
import type { ChatTopic } from "../types";
import { historyAction, fetchReportByTopic } from "../services/api";
import { FaEllipsisV } from "react-icons/fa";

interface Props {
  item: ChatTopic;
  onOpen: (topic: string) => void;
  onRefresh: () => void;
  currentTopic?: string | null;
}

const ChatHistoryItem: React.FC<Props> = ({ item, onOpen, onRefresh, currentTopic }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [reportId, setReportId] = useState<number | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const closeOnOutside = (e: MouseEvent) => {
      if (!menuRef.current) return;
      if (!menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("click", closeOnOutside);
    return () => document.removeEventListener("click", closeOnOutside);
  }, []);

  const ensureReportId = async () => {
    if (reportId != null) return reportId;
    const meta = await fetchReportByTopic(item.topic);
    const id = meta && typeof meta.id !== "undefined" ? meta.id : null;
    setReportId(id);
    return id;
  };

  const doAction = async (action: "share" | "rename" | "archive" | "delete") => {
    const id = await ensureReportId();
    if (!id) {
      alert("No report found for this topic.");
      return;
    }
    try {
      if (action === "share") {
        const data = await historyAction(id, "share");
        const full = location.origin + (data.share_url || "");
        window.prompt("Share link (copy):", full);
      } else if (action === "rename") {
        const newName = window.prompt("New topic name:", item.topic);
        if (!newName || newName.trim() === item.topic) return;
        await historyAction(id, "rename", newName.trim());
        onRefresh();
      } else if (action === "archive") {
        if (!window.confirm("Archive this report topic?")) return;
        await historyAction(id, "archive");
        if (currentTopic === item.topic) {
          // parent will clear view on refresh
        }
        onRefresh();
      } else if (action === "delete") {
        if (!window.confirm("Delete this report topic permanently?")) return;
        await historyAction(id, "delete");
        if (currentTopic === item.topic) {
          // parent will clear view on refresh
        }
        onRefresh();
      }
    } catch (e: any) {
      alert(e?.message || "Action failed");
    } finally {
      setMenuOpen(false);
    }
  };

  return (
    <div
      className={`relative p-3 rounded-lg mb-2 cursor-pointer transition-colors ${
        currentTopic === item.topic ? "bg-gray-700" : "bg-gray-700/70 hover:bg-gray-600"
      }`}
      onClick={(e) => {
        // ignore clicks on the menu button
        const target = e.target as HTMLElement;
        if (target.closest(".history-menu")) return;
        onOpen(item.topic);
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm text-white truncate">
            {item.topic}
            <span className="ml-2 text-xs inline-block px-2 py-0.5 rounded-full bg-emerald-500 text-white align-middle">
              topic
            </span>
          </div>
          <div className="text-[11px] text-gray-300 mt-1 truncate">
            {new Date(item.last_at).toLocaleString()} • {item.count} items
          </div>
        </div>

        {/* Ellipsis menu */}
        <div className="history-menu relative" ref={menuRef}>
          <button
            type="button"
            className="p-1.5 text-gray-200 hover:bg-white/10 rounded-md"
            onClick={async (e) => {
              e.stopPropagation();
              // preload id to enable/disable
              await ensureReportId();
              setMenuOpen((s) => !s);
            }}
            title="More"
          >
            <FaEllipsisV />
          </button>

          {menuOpen && (
            <div className="absolute right-0 mt-2 w-40 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-10">
              <button
                disabled={!reportId}
                className={`w-full text-left text-sm px-3 py-2 hover:bg-gray-800 ${
                  !reportId ? "opacity-50 cursor-not-allowed" : "text-gray-100"
                }`}
                onClick={(e) => {
                  e.stopPropagation();
                  doAction("share");
                }}
              >
                Share
              </button>
              <button
                disabled={!reportId}
                className={`w-full text-left text-sm px-3 py-2 hover:bg-gray-800 ${
                  !reportId ? "opacity-50 cursor-not-allowed" : "text-gray-100"
                }`}
                onClick={(e) => {
                  e.stopPropagation();
                  doAction("rename");
                }}
              >
                Rename
              </button>
              <button
                disabled={!reportId}
                className={`w-full text-left text-sm px-3 py-2 hover:bg-gray-800 ${
                  !reportId ? "opacity-50 cursor-not-allowed" : "text-gray-100"
                }`}
                onClick={(e) => {
                  e.stopPropagation();
                  doAction("archive");
                }}
              >
                Archive
              </button>
              <button
                disabled={!reportId}
                className={`w-full text-left text-sm px-3 py-2 hover:bg-gray-800 text-red-300 ${
                  !reportId ? "opacity-50 cursor-not-allowed" : ""
                }`}
                onClick={(e) => {
                  e.stopPropagation();
                  doAction("delete");
                }}
              >
                Delete
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatHistoryItem;
