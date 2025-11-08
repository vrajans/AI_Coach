import React, { useState, useEffect, useRef } from "react";
import SessionList from "./SessionList";
import ResumeSidebar from "./ResumeSidebar";
import EngineInspector from "./EngineInspector";
import LearningTimeline from "./LearningTimeline";

const API_URL =
  window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost"
    ? "http://127.0.0.1:8000"
    : window.location.origin;

const BOT_AVATAR = "https://api.dicebear.com/7.x/bottts/svg?seed=ai";
const USER_AVATAR = "https://api.dicebear.com/7.x/notionists/svg?seed=user";

export default function ChatUI() {
  /* ------------------------- STATE -------------------------- */
  const [sessions, setSessions] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("sessions") || "[]");
    } catch {
      return [];
    }
  });

  const [activeUserId, setActiveUserId] = useState(
    () => localStorage.getItem("userId") || (sessions[0] && sessions[0].user_id) || ""
  );

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [botTyping, setBotTyping] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [uploadBanner, setUploadBanner] = useState(null);

  const scrollRef = useRef();

  /* ------------------------ LOAD CHAT ------------------------ */
  useEffect(() => {
    if (activeUserId) {
      const saved = JSON.parse(localStorage.getItem(`chatHistory_${activeUserId}`) || "[]");
      setMessages(saved);
      localStorage.setItem("userId", activeUserId);
    }
  }, [activeUserId]);

  useEffect(() => {
    localStorage.setItem("sessions", JSON.stringify(sessions));
  }, [sessions]);

  useEffect(() => {
    if (activeUserId) {
      localStorage.setItem(`chatHistory_${activeUserId}`, JSON.stringify(messages));
    }
  }, [messages, activeUserId]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, botTyping]);

  const activeSession = sessions.find((s) => s.user_id === activeUserId);

  /* ------------------------ UPLOAD FILE ------------------------ */
  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    const form = new FormData();
    form.append("file", file);
    setBotTyping(true);

    try {
      const resp = await fetch(`${API_URL}/upload_resume/`, {
        method: "POST",
        body: form
      });
      const data = await resp.json();
      setBotTyping(false);

      if (data.user_id) {
        const newSession = {
          user_id: data.user_id,
          fileName: file.name,
          parsed_resume: data.parsed_resume,
          created_at: new Date().toISOString()
        };

        setSessions((prev) => [newSession, ...prev.filter((s) => s.user_id !== newSession.user_id)]);
        setActiveUserId(newSession.user_id);

        setMessages([
          {
            sender: "bot",
            text: "✅ Resume uploaded. Ask me career or skills questions!",
            time: new Date().toISOString()
          }
        ]);

        setUploadBanner({
          fileName: file.name,
          userId: data.user_id,
          time: new Date().toLocaleString()
        });

        setTimeout(() => setUploadBanner(null), 7000);
      }
    } catch {
      setBotTyping(false);
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "⚠️ Upload error.", time: new Date().toISOString() }
      ]);
    }
  }

  /* ------------------------ SEND MESSAGE ------------------------ */
  async function sendMessage() {
    if (!input.trim() || !activeUserId) return;

    const userMsg = { sender: "user", text: input.trim(), time: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);

    const question = input.trim();
    setInput("");
    setBotTyping(true);

    try {
      const resp = await fetch(`${API_URL}/chat/${activeUserId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question })
      });

      const data = await resp.json();

      // const botMsg = {
      //   sender: "bot",
      //   text: (data.answer || "No response").trim(),
      //   engine_context: data.engine_context_used || null,
      //   source_documents: data.source_documents || [],
      //   learning_plan: data.learning_plan || null,
      //   time: new Date().toISOString()
      // };

      function safeClone(value) {
          try {
            return JSON.parse(JSON.stringify(value));
          } 
          catch (e) {
            console.warn("Failed to clone engine_context:", e);
            return null;
          }
        }

      const formatEngineContext = (ctx) => {
        if (!ctx) return null;
        let lines = [];
        if (ctx.domain) lines.push(`Domain: ${ctx.domain}`);
        if (ctx.primary_occupation) lines.push(`Occupation: ${ctx.primary_occupation}`);
        if (ctx.occupation_meta?.canonical) lines.push(`Canonical Occupation: ${ctx.occupation_meta.canonical}`);
        if (ctx.skill_gaps?.length) lines.push(`Skill Gaps: ${ctx.skill_gaps.join(", ")}`);
        if (ctx.learning_plan?.summary) lines.push(`Learning Plan: ${ctx.learning_plan.summary}`);
        return lines.join("\n");
      };

      const botMsg = {
        sender: "bot",
        text: typeof data.answer === "string" ? data.answer.trim() : "Invalid response",
        engine_context: safeClone(data.engine_context_used),   // ✅ fully sanitized
        source_documents: Array.isArray(data.source_documents) ? data.source_documents : [],
        learning_plan: data.learning_plan || null,
        time: new Date().toISOString()
      };

      // Construct the bot message
      // const botMsg = {
      //   sender: "bot",
      //   text: (data.answer || "No response").trim(),
      //   engine_context: formatEngineContext(data.engine_context_used),
      //   source_documents: data.source_documents || [],
      //   learning_plan: data.learning_plan || null,
      //   time: new Date().toISOString()
      // };


      // const botMsg = {
      //   sender: "bot",
      //   text: (data.answer || "No response").trim(),
      //   engine_context: data.engine_context_used || null,
      //   engine_context_raw: data.engine_context_used || null,
      //   source_documents: data.source_documents || [],
      //   learning_plan: data.learning_plan || null,
      //   time: new Date().toISOString()
      // };

      setMessages((prev) => [...prev, botMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "⚠️ Unable to reach server.", time: new Date().toISOString() }
      ]);
    } finally {
      setBotTyping(false);
    }
  }

  function deleteSession(user_id) {
    setSessions((prev) => prev.filter((s) => s.user_id !== user_id));
    localStorage.removeItem(`chatHistory_${user_id}`);

    if (activeUserId === user_id) {
      const remaining = sessions.filter((s) => s.user_id !== user_id);
      setActiveUserId(remaining[0]?.user_id || "");
    }
  }

  function clearActiveChat() {
    if (!activeUserId) return;
    localStorage.removeItem(`chatHistory_${activeUserId}`);
    setMessages([]);
  }

  function formatTime(ts) {
    return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function formatText(text) {
    return text.split("\n").map((line, i) => (
      <p key={i} className="mb-2 leading-relaxed">{line}</p>
    ));
  }

  /* ------------------------ UI LAYOUT ------------------------ */

  return (
    <div className="h-screen w-screen flex overflow-hidden bg-slate-100">

      {/* ✅ FIXED LEFT SIDEBAR */}
      <aside className="w-72 bg-white border-r flex-shrink-0 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <div className="text-sm font-semibold">AI Coach</div>
          <label className="text-xs text-indigo-600 cursor-pointer bg-indigo-50 px-2 py-1 rounded">
            Upload
            <input type="file" className="hidden" onChange={handleUpload} />
          </label>
        </div>

        <div className="h-[calc(100vh-60px)] overflow-y-auto">
          <SessionList
            sessions={sessions}
            activeUserId={activeUserId}
            onSelect={(id) => setActiveUserId(id)}
            onDelete={deleteSession}
          />
        </div>
      </aside>

      {/* ✅ CENTER CHAT AREA */}
      <div className="flex-1 flex flex-col max-w-5xl mx-auto">

        {/* HEADER */}
        <div className="flex items-center justify-between p-4 bg-white border-b flex-shrink-0">
          <div className="flex items-center gap-4">
            <div className="text-lg font-semibold">🤖 AI Career Coach</div>
            {activeSession && (
              <div className="text-sm text-gray-500 truncate max-w-[200px]">
                Resume: <strong>{activeSession.fileName}</strong>
              </div>
            )}
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="px-3 py-1 rounded bg-gray-100 text-sm"
            >
              Toggle Summary
            </button>
            <button
              onClick={clearActiveChat}
              className="px-3 py-1 rounded bg-red-50 text-red-600 text-sm"
            >
              Clear Chat
            </button>
          </div>
        </div>

        {/* ✅ UPLOAD BANNER */}
        {uploadBanner && (
          <div className="mx-auto max-w-4xl mt-3">
            <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-2 rounded text-sm">
              ✅ <strong>{uploadBanner.fileName}</strong> uploaded for <strong>{uploadBanner.userId}</strong>
            </div>
          </div>
        )}

        {/* ✅ CHAT SCROLL AREA */}
        <div className="flex-1 overflow-hidden flex">
          <div className="flex-1 flex flex-col">
            <main className="flex-1 overflow-y-auto p-6 bg-gray-50">

              {messages.map((m, idx) => (
                <div key={idx} className={`mb-4 ${m.sender === "user" ? "text-right" : ""}`}>

                  <div className={`flex items-start ${m.sender === "user" ? "justify-end" : ""}`}>
                    {m.sender === "bot" && (
                      <img src={BOT_AVATAR} className="w-10 h-10 rounded-full mr-3" alt="bot" />
                    )}

                    <div
                      className={`max-w-[75%] px-5 py-3 rounded-2xl shadow-sm ${
                        m.sender === "user"
                          ? "bg-indigo-600 text-white"
                          : "bg-white text-gray-900 border border-gray-100"
                      }`}
                    >
                      {m.sender === "bot" ? formatText(m.text) : m.text}
                      <div className="text-xs text-gray-400 mt-1 text-right">
                        {formatTime(m.time)}
                      </div>
                    </div>

                    {m.sender === "user" && (
                      <img src={USER_AVATAR} className="w-10 h-10 rounded-full ml-3" alt="user" />
                    )}
                  </div>

                  {/* ✅ ENGINE INSPECTOR */}
                  {m.engine_context && (
                    <div className="mt-3">
                      <EngineInspector
                        engineContext={m.engine_context}
                        sourceDocs={m.source_documents}
                      />
                    </div>
                  )}

                  {/* ✅ LEARNING TIMELINE */}
                  {m.learning_plan && (
                    <div className="mt-3">
                      <LearningTimeline plan={m.learning_plan} />
                    </div>
                  )}
                </div>
              ))}

              {botTyping && (
                <div className="flex items-center gap-2 text-gray-500">
                  <img src={BOT_AVATAR} className="w-6 h-6" alt="typing" />
                  <span className="animate-pulse">AI is typing...</span>
                </div>
              )}

              <div ref={scrollRef} />
            </main>

            {/* INPUT BAR */}
            <div className="p-4 bg-white border-t flex gap-3">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                placeholder="Ask your career question..."
                className="flex-1 border rounded-full px-4 py-2"
              />
              <button
                onClick={sendMessage}
                className="bg-indigo-600 text-white px-4 py-2 rounded-full"
              >
                Send
              </button>
            </div>
          </div>

          {/* ✅ FIXED RIGHT SIDEBAR */}
          <aside
            className={`w-80 bg-white border-l overflow-y-auto h-screen ${
              sidebarOpen ? "" : "hidden md:block"
            }`}
          >
            <ResumeSidebar
              parsed_resume={activeSession?.parsed_resume}
              onClose={() => setSidebarOpen(false)}
            />
          </aside>
        </div>
      </div>
    </div>
  );
}
