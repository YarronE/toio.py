import React, { useState, useRef, useEffect } from "react";
import { usePetStore } from "../store/petStore";

interface ChatPanelProps {
  visible: boolean;
  onToggle: () => void;
}

/**
 * 聊天交互面板
 *
 * 包含消息历史、输入框。悬浮在桌宠旁边。
 */
export const ChatPanel: React.FC<ChatPanelProps> = ({ visible, onToggle }) => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Array<{ role: string; text: string; mood?: string }>>([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { sendChat, mood, name } = usePetStore();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (visible) inputRef.current?.focus();
  }, [visible]);

  const handleSend = async () => {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: msg }]);
    setLoading(true);

    try {
      const resp = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg }),
      });
      const data = await resp.json();
      setMessages((prev) => [...prev, { role: "pet", text: data.text, mood: data.mood }]);
    } catch (e) {
      setMessages((prev) => [...prev, { role: "pet", text: "呜...连接不上后端 😿" }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!visible) {
    return (
      <button
        onClick={onToggle}
        style={{
          position: "fixed",
          bottom: 180,
          right: 30,
          width: 48,
          height: 48,
          borderRadius: "50%",
          border: "none",
          background: "linear-gradient(135deg, #667eea, #764ba2)",
          color: "#fff",
          fontSize: 22,
          cursor: "pointer",
          boxShadow: "0 4px 15px rgba(102,126,234,0.4)",
          pointerEvents: "auto",
          zIndex: 9998,
        }}
        title="打开聊天"
      >
        💬
      </button>
    );
  }

  return (
    <div
      style={{
        position: "fixed",
        bottom: 20,
        right: 20,
        width: 360,
        height: 480,
        background: "rgba(255,255,255,0.97)",
        borderRadius: 18,
        boxShadow: "0 12px 40px rgba(0,0,0,0.2)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        fontFamily: "'Segoe UI', sans-serif",
        pointerEvents: "auto",
        zIndex: 9998,
      }}
    >
      {/* 头部 */}
      <div
        style={{
          padding: "12px 16px",
          background: "linear-gradient(135deg, #667eea, #764ba2)",
          color: "#fff",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <span style={{ fontWeight: 700, fontSize: 15 }}>🐾 {name || "小宠"}</span>
          <span
            style={{
              marginLeft: 8,
              fontSize: 11,
              background: "rgba(255,255,255,0.2)",
              padding: "2px 8px",
              borderRadius: 10,
            }}
          >
            {mood}
          </span>
        </div>
        <button
          onClick={onToggle}
          style={{
            background: "rgba(255,255,255,0.2)",
            border: "none",
            color: "#fff",
            borderRadius: 8,
            width: 28,
            height: 28,
            cursor: "pointer",
            fontSize: 14,
          }}
        >
          ✕
        </button>
      </div>

      {/* 消息区 */}
      <div ref={scrollRef} style={{ flex: 1, overflow: "auto", padding: 12 }}>
        {messages.length === 0 && (
          <div style={{ textAlign: "center", color: "#bbb", marginTop: 60 }}>
            <div style={{ fontSize: 40, marginBottom: 8 }}>🐾</div>
            <div>跟我聊聊天吧~</div>
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              justifyContent: m.role === "user" ? "flex-end" : "flex-start",
              marginBottom: 10,
            }}
          >
            <div
              style={{
                maxWidth: "80%",
                padding: "8px 14px",
                borderRadius: m.role === "user" ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
                background: m.role === "user" ? "#667eea" : "#f0f0f0",
                color: m.role === "user" ? "#fff" : "#333",
                fontSize: 14,
                lineHeight: 1.5,
                wordBreak: "break-word",
              }}
            >
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 10 }}>
            <div
              style={{
                padding: "8px 14px",
                borderRadius: "14px 14px 14px 4px",
                background: "#f0f0f0",
                color: "#999",
                fontSize: 14,
              }}
            >
              正在思考...
            </div>
          </div>
        )}
      </div>

      {/* 输入区 */}
      <div style={{ padding: 12, borderTop: "1px solid #eee", display: "flex", gap: 8 }}>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="跟桌宠说点什么..."
          style={{
            flex: 1,
            padding: "8px 14px",
            borderRadius: 12,
            border: "2px solid #e0e0e0",
            outline: "none",
            fontSize: 14,
          }}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          style={{
            padding: "8px 16px",
            borderRadius: 12,
            border: "none",
            background: loading || !input.trim() ? "#ccc" : "linear-gradient(135deg, #667eea, #764ba2)",
            color: "#fff",
            cursor: loading ? "wait" : "pointer",
            fontWeight: 600,
          }}
        >
          发送
        </button>
      </div>
    </div>
  );
};
