import React from "react";

interface ChatBubbleProps {
  message: string;
  mood: string;
}

/**
 * 聊天气泡组件
 */
export const ChatBubble: React.FC<ChatBubbleProps> = ({ message, mood }) => {
  const moodEmoji: Record<string, string> = {
    happy: "😊",
    excited: "🎉",
    calm: "😌",
    curious: "🤔",
    sleepy: "😴",
    sad: "😢",
    playful: "😸",
  };

  return (
    <div
      style={{
        position: "absolute",
        bottom: 150,
        left: "50%",
        transform: "translateX(-50%)",
        maxWidth: 300,
        padding: "12px 16px",
        background: "rgba(255, 255, 255, 0.95)",
        borderRadius: 16,
        boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
        fontSize: 14,
        lineHeight: 1.5,
        color: "#333",
        pointerEvents: "auto",
      }}
    >
      <span style={{ marginRight: 4 }}>{moodEmoji[mood] || "🐾"}</span>
      {message}
      {/* 气泡尾巴 */}
      <div
        style={{
          position: "absolute",
          bottom: -8,
          left: "50%",
          marginLeft: -8,
          width: 0,
          height: 0,
          borderLeft: "8px solid transparent",
          borderRight: "8px solid transparent",
          borderTop: "8px solid rgba(255, 255, 255, 0.95)",
        }}
      />
    </div>
  );
};
