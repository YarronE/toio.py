import React, { useEffect, useState, useCallback } from "react";
import { usePetStore } from "./store/petStore";
import { PetCanvas } from "./components/PetCanvas";
import { ChatBubble } from "./components/ChatBubble";
import { ChatPanel } from "./components/ChatPanel";
import { CreationWizard } from "./components/CreationWizard";

export default function App() {
  const { mood, message, isPhysical, x, y, connect, connected } = usePetStore();
  const [chatOpen, setChatOpen] = useState(false);
  const [showWizard, setShowWizard] = useState(false);
  const [created, setCreated] = useState(() => !!localStorage.getItem("pet_created"));
  const [bubbleMsg, setBubbleMsg] = useState("");
  const [bubbleTimer, setBubbleTimer] = useState<NodeJS.Timeout | null>(null);

  // 启动时连接 WebSocket
  useEffect(() => {
    if (!connected) connect();
  }, []);

  // 首次启动显示创建向导
  useEffect(() => {
    if (!created) setShowWizard(true);
  }, [created]);

  // 收到新消息时显示气泡
  useEffect(() => {
    if (message) {
      setBubbleMsg(message);
      if (bubbleTimer) clearTimeout(bubbleTimer);
      const t = setTimeout(() => setBubbleMsg(""), 6000);
      setBubbleTimer(t);
    }
  }, [message]);

  const handleCreationComplete = () => {
    setShowWizard(false);
    setCreated(true);
    localStorage.setItem("pet_created", "true");
  };

  // 鼠标穿透控制
  const handlePetMouseEnter = useCallback(() => {
    window.electronAPI?.setIgnoreMouse(false);
  }, []);
  const handlePetMouseLeave = useCallback(() => {
    window.electronAPI?.setIgnoreMouse(true);
  }, []);

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        position: "relative",
        pointerEvents: "none",
        background: "transparent",
      }}
    >
      {/* 创建向导 */}
      {showWizard && <CreationWizard onComplete={handleCreationComplete} />}

      {/* 桌宠 */}
      {!showWizard && (
        <>
          <div
            onMouseEnter={handlePetMouseEnter}
            onMouseLeave={handlePetMouseLeave}
            onDoubleClick={() => setChatOpen(!chatOpen)}
            style={{
              pointerEvents: "auto",
              position: "absolute",
              left: x - 64,
              top: y - 64,
              cursor: "pointer",
              transition: "left 0.3s ease, top 0.3s ease",
            }}
          >
            <PetCanvas mood={mood} isPhysical={isPhysical} />
          </div>

          {/* 对话气泡 */}
          {bubbleMsg && !chatOpen && (
            <div style={{ position: "absolute", left: x - 150, top: y - 100, pointerEvents: "none" }}>
              <ChatBubble message={bubbleMsg} mood={mood} />
            </div>
          )}

          {/* 聊天面板 */}
          <ChatPanel visible={chatOpen} onToggle={() => setChatOpen(!chatOpen)} />

          {/* 连接状态指示 */}
          <div
            style={{
              position: "fixed",
              bottom: 8,
              left: 8,
              fontSize: 11,
              color: connected ? "#4CAF50" : "#f44336",
              pointerEvents: "none",
              opacity: 0.6,
            }}
          >
            ● {connected ? "已连接" : "断开"}
          </div>
        </>
      )}
    </div>
  );
}
