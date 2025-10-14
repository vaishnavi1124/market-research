// frontend/src/components/Chatbot.tsx
import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { FiSend } from "react-icons/fi";
import { FaRobot } from "react-icons/fa";
import { IoIosMic, IoIosMicOff } from "react-icons/io";
import { FcSpeaker } from "react-icons/fc";
import { ImVolumeMute2 } from "react-icons/im";
import { FaThumbsUp, FaThumbsDown } from "react-icons/fa";

const API_BASE =
  (import.meta as any)?.env?.VITE_API_URL || "http://127.0.0.1:8000";

interface ChatMessage {
  role: "user" | "bot";
  text: string;
  id: number;
  feedback?: "like" | "dislike";
  suggestions?: string[]; // follow-up suggestions tied to this bot message
}

interface ChatbotProps {
  topic: string | null; // current topic from Sidebar/Dashboard
  newChatNonce: number; // increments on "New Chat"
  onHistoryChange: () => void; // refresh Sidebar history after send

  // Allow Dashboard to push suggestions into Chatbot
  externalSuggestions?: string[] | null;
  externalIntroText?: string | null;
}

const playSound = (src: string) => {
  const audio = new Audio(src);
  audio.play().catch(() => {});
};

const Chatbot: React.FC<ChatbotProps> = ({
  topic,
  newChatNonce,
  onHistoryChange,
  externalSuggestions,
  externalIntroText,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [query, setQuery] = useState("");
  const [listening, setListening] = useState(false);
  const [speakingId, setSpeakingId] = useState<number | null>(null);
  const recognitionRef = useRef<any | null>(null);
  const synthRef = useRef(window.speechSynthesis);
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const msgId = useRef(0);
  const lastSugSigRef = useRef<string | null>(null);

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load full thread for a topic
  useEffect(() => {
    let ignore = false;

    async function loadThread(t: string) {
      try {
        const r = await fetch(
          `${API_BASE}/api/chat-thread?topic=${encodeURIComponent(t)}`,
          { credentials: "include" }
        );
        if (!r.ok) throw new Error("Failed to fetch chat thread");
        const rows: Array<{ id: number; role: string; message: string }> =
          await r.json();

        if (!ignore) {
          const mapped: ChatMessage[] = rows.map((m) => ({
            id: m.id,
            role: m.role === "user" ? "user" : "bot",
            text: m.message || "",
          }));
          setMessages(mapped);
          msgId.current = (rows.at(-1)?.id || 0) + 1;
        }
      } catch {
        if (!ignore) setMessages([]);
      }
    }

    if (topic) {
      loadThread(topic);
    } else {
      // "New Chat" clears the pane
      setMessages([]);
      msgId.current = 0;
    }

    // reset last suggestion signature on topic/new chat change
    lastSugSigRef.current = null;

    return () => {
      ignore = true;
    };
  }, [topic, newChatNonce]);

  // When Dashboard sends suggestions, show them as a bot message in Chatbot
  useEffect(() => {
    if (!externalSuggestions || externalSuggestions.length === 0) return;
    const clean = externalSuggestions.filter((s: string) => s && s.trim());
    if (clean.length === 0) return;

    // Prevent duplicate suggestion drops if same list arrives repeatedly
    const signature = JSON.stringify(clean);
    if (lastSugSigRef.current === signature) return;
    lastSugSigRef.current = signature;

    const text =
      (externalIntroText && externalIntroText.trim()) ||
      "Here are some suggested follow-up questions based on the report:";

    setMessages((prev) => [
      ...prev,
      {
        role: "bot",
        text,
        id: msgId.current++,
        suggestions: clean,
      },
    ]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [externalSuggestions, externalIntroText]);

  // Voice input
  const toggleListening = () => {
    const SR: any = (window as any).webkitSpeechRecognition;
    if (!SR) {
      alert("Speech recognition not supported in this browser");
      return;
    }

    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
    } else {
      const recognition = new SR();
      recognition.lang = "en-US";
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setQuery((prev) => (prev ? prev + " " : "") + transcript);
      };

      recognition.onerror = () => setListening(false);
      recognition.onend = () => setListening(false);

      recognition.start();
      recognitionRef.current = recognition;
      setListening(true);
    }
  };

  // Bot voice (speak once per click)
  const speakMessage = (id: number, text: string) => {
    if (speakingId === id) {
      synthRef.current.cancel();
      setSpeakingId(null);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(
      text.replace(/[#*_`>~-]/g, "")
    );
    utterance.onend = () => setSpeakingId(null);
    synthRef.current.cancel();
    synthRef.current.speak(utterance);
    setSpeakingId(id);
  };

  const sendMessage = async (explicitText?: string) => {
    // allow sending even without topic; just guard empty input
    const toSend = explicitText ?? query;
    if (!toSend.trim()) return;
    playSound("/sounds/keyboard-typing-one-short-1-292590.mp3");

    const newId = msgId.current++;
    const newMsg: ChatMessage = { role: "user", text: toSend, id: newId };

    // optimistic UI
    setMessages((prev) => [
      ...prev,
      newMsg,
      { role: "bot", text: "💭 thinking…", id: msgId.current++ },
    ]);

    try {
      const params = new URLSearchParams({ query: toSend });
      if (topic) params.set("topic", topic);

      const resp = await fetch(`${API_BASE}/chatbot`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        credentials: "include",
        body: params,
      });

      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || "Chatbot error");

      const suggestions: string[] = Array.isArray(data.suggestions)
        ? (data.suggestions as unknown[]).reduce<string[]>((acc, v) => {
            if (typeof v === "string" && v.trim()) acc.push(v.trim());
            else if (v && typeof v === "object") {
              const anyV = v as any;
              const cand =
                anyV?.question ?? anyV?.text ?? anyV?.q ?? String(anyV ?? "");
              if (typeof cand === "string" && cand.trim())
                acc.push(cand.trim());
            }
            return acc;
          }, [])
        : [];

      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "bot", text: data.response, id: msgId.current++, suggestions },
      ]);

      // refresh chat-history counters/timestamps
      onHistoryChange();

      playSound("/sounds/new-notification-010-352755.mp3");
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Unknown error occurred";
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "bot", text: `❌ Error: ${errorMessage}`, id: msgId.current++ },
      ]);
    }
    if (!explicitText) setQuery("");
  };

  // Suggestion click → auto ask follow-up
  const handleSuggestionClick = (suggestion: string) => {
    sendMessage(suggestion);
  };

  // Send feedback (like/dislike)
  const sendFeedback = async (id: number, feedback: "like" | "dislike") => {
    const msg = messages.find((m) => m.id === id && m.role === "bot");
    if (!msg) return;

    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, feedback } : m))
    );

    try {
      await fetch(`${API_BASE}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ message: msg.text, feedback, topic }),
      });
    } catch {
      /* noop */
    }
  };

  return (
    <div className="mx-auto p-1 ">
      <div className="bg-trnsparant backdrop-blur-md  overflow-hidden flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-2 space-y-auto">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-4 ${
                msg.role === "user" ? "flex-row-reverse" : ""
              }`}
            >
              {/* Avatar */}
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                  msg.role === "user"
                    ? "bg-slate-200 text-slate-600"
                    : "bg-indigo-600 text-white"
                }`}
              >
                {msg.role === "user" ? "You" : <FaRobot />}
              </div>

              {/* Bubble */}
              <div className={`flex-1 ${msg.role === "user" ? "text-right" : ""}`}>
                <div
                  className={`inline-block max-w-[85%] ${
                    msg.role === "user"
                      ? "bg-slate-800 text-white rounded-2xl rounded-tr-md px-4 py-1"
                      : "bg-white/80 border border-gray-200/80 text-gray-800 rounded-2xl px-4 py-1"
                  }`}
                >
                  {msg.role === "user" ? (
                    <p className="text-sm leading-relaxed">{msg.text}</p>
                  ) : (
                    <div className="prose prose-sm max-w-none text-gray-800">
                      <ReactMarkdown>{msg.text}</ReactMarkdown>
                    </div>
                  )}
                </div>

                {/* Controls for bot messages */}
                {msg.role === "bot" && (
                  <div className="flex flex-col gap-2 mt-2">
                    {/* Voice + Like/Dislike */}
                    <div className="flex gap-4 items-center">
                      {/* Voice */}
                      <button
                        onClick={() => speakMessage(msg.id, msg.text)}
                        className="text-xl"
                        title={speakingId === msg.id ? "Stop" : "Speak"}
                      >
                        {speakingId === msg.id ? (
                          <ImVolumeMute2 className="text-red-500" />
                        ) : (
                          <FcSpeaker />
                        )}
                      </button>

                      {/* Like / Dislike */}
                      <button
                        onClick={() => sendFeedback(msg.id, "like")}
                        className={`text-lg ${
                          msg.feedback === "like" ? "text-green-600" : "text-gray-400"
                        }`}
                        title="Helpful"
                      >
                        <FaThumbsUp />
                      </button>
                      <button
                        onClick={() => sendFeedback(msg.id, "dislike")}
                        className={`text-lg ${
                          msg.feedback === "dislike" ? "text-red-500" : "text-gray-400"
                        }`}
                        title="Not helpful"
                      >
                        <FaThumbsDown />
                      </button>
                    </div>

                    {/* Suggested follow-ups */}
                    {msg.suggestions && msg.suggestions.length > 0 && (
                      <div className="flex flex-wrap gap-2 pt-1">
                        {msg.suggestions.map((sug, idx) => (
                          <button
                            key={`${msg.id}-sug-${idx}`}
                            onClick={() => handleSuggestionClick(sug)}
                            className="px-3 py-1.5 text-xs rounded-b-full border border-indigo-200 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 transition-colors"
                            title="Ask this follow-up"
                          >
                            {sug}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-300/60 p-2 bg-white/60">
          <div className="flex items-end gap-3">
            <button
              onClick={toggleListening}
              className="w-10 h-10 rounded-full flex items-center justify-center bg-gray-200 hover:bg-gray-300"
              title={listening ? "Stop voice input" : "Start voice input"}
            >
              {listening ? (
                <IoIosMicOff size={30} className="text-red-600" />
              ) : (
                <IoIosMic size={30} className="text-indigo-600" />
              )}
            </button>

            <div className="flex-1 relative">
              <input
                type="text"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  if (e.target.value.length > query.length) {
                    playSound("/sounds/sound-1-167181.mp3");
                  }
                }}
                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                placeholder={topic ? `Ask about "${topic}"…` : "Ask Copilot…"}
                className="w-full border border-gray-300 rounded-xl px-4 py-1 pr-12 text-gray-700 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-white/80"
              />
            </div>
            <button
              onClick={() => sendMessage()}
              disabled={!query.trim()}
              className={`w-10 h-10 rounded-b-full flex items-center justify-center transition-colors ${
                query.trim()
                  ? "bg-indigo-600 hover:bg-indigo-700 text-white"
                  : "bg-gray-200 text-gray-400 cursor-not-allowed"
              }`}
              title="Send"
            >
              <FiSend size={24} />
            </button>
          </div>

          {/* Topic hint */}
          <div className="text-[11px] text-gray-500 mt-2">
            {topic ? (
              <>You’re chatting under: <span className="font-medium">{topic}</span></>
            ) : (
              <>No topic selected — your chat won’t be attached to a report.</>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chatbot;
