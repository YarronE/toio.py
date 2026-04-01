import React, { useState, useRef } from "react";
import { usePetStore } from "../store/petStore";

interface CreationWizardProps {
  onComplete: () => void;
}

/**
 * 桌宠创建向导
 *
 * 用户可以通过照片上传或文字描述创建自己的桌宠形象。
 */
export const CreationWizard: React.FC<CreationWizardProps> = ({ onComplete }) => {
  const [step, setStep] = useState<"name" | "appearance" | "generating" | "done">("name");
  const [petName, setPetName] = useState("");
  const [description, setDescription] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [style, setStyle] = useState("chibi");
  const fileRef = useRef<HTMLInputElement>(null);
  const { sendChat } = usePetStore();

  const styles = [
    { id: "chibi", label: "Q版", emoji: "🧸" },
    { id: "pixel", label: "像素", emoji: "👾" },
    { id: "anime", label: "动漫", emoji: "✨" },
    { id: "realistic", label: "写实", emoji: "🎨" },
  ];

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleGenerate = async () => {
    setStep("generating");

    try {
      // 通过 REST API 调用 AIGC 生成
      const resp = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: `帮我生成一个桌宠形象：${description || "可爱的小猫"}，风格：${style}`,
        }),
      });
      const data = await resp.json();
      console.log("生成结果:", data);
    } catch (e) {
      console.error("生成失败:", e);
    }

    // 设置桌宠名字
    try {
      await fetch("http://localhost:8000/api/pet/name", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: petName || "小宠" }),
      });
    } catch (e) {
      console.error(e);
    }

    setStep("done");
  };

  const panelStyle: React.CSSProperties = {
    position: "fixed",
    top: "50%",
    left: "50%",
    transform: "translate(-50%, -50%)",
    width: 420,
    background: "rgba(255,255,255,0.97)",
    borderRadius: 20,
    padding: 32,
    boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
    fontFamily: "'Segoe UI', sans-serif",
    color: "#333",
    pointerEvents: "auto",
    zIndex: 9999,
  };

  const btnStyle: React.CSSProperties = {
    padding: "10px 24px",
    borderRadius: 12,
    border: "none",
    background: "linear-gradient(135deg, #667eea, #764ba2)",
    color: "#fff",
    fontSize: 15,
    fontWeight: 600,
    cursor: "pointer",
    transition: "transform 0.1s",
  };

  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "10px 14px",
    borderRadius: 10,
    border: "2px solid #e0e0e0",
    fontSize: 15,
    outline: "none",
    transition: "border-color 0.2s",
  };

  return (
    <div style={panelStyle}>
      {/* Step 1: 起名 */}
      {step === "name" && (
        <div>
          <h2 style={{ margin: "0 0 8px", fontSize: 22 }}>🐾 创建你的桌宠</h2>
          <p style={{ color: "#888", margin: "0 0 20px", fontSize: 14 }}>给你的虚拟伙伴起个名字吧</p>
          <input
            style={inputStyle}
            placeholder="桌宠名字（如：小团子）"
            value={petName}
            onChange={(e) => setPetName(e.target.value)}
            autoFocus
          />
          <div style={{ marginTop: 20, textAlign: "right" }}>
            <button style={btnStyle} onClick={() => setStep("appearance")}>
              下一步 →
            </button>
          </div>
        </div>
      )}

      {/* Step 2: 外观设计 */}
      {step === "appearance" && (
        <div>
          <h2 style={{ margin: "0 0 8px", fontSize: 22 }}>✨ 设计 {petName || "桌宠"} 的外观</h2>
          <p style={{ color: "#888", margin: "0 0 16px", fontSize: 14 }}>上传照片或用文字描述</p>

          {/* 上传照片 */}
          <div
            onClick={() => fileRef.current?.click()}
            style={{
              border: "2px dashed #ccc",
              borderRadius: 12,
              padding: 20,
              textAlign: "center",
              cursor: "pointer",
              marginBottom: 16,
              background: previewUrl ? "none" : "#fafafa",
            }}
          >
            {previewUrl ? (
              <img src={previewUrl} alt="preview" style={{ maxWidth: "100%", maxHeight: 150, borderRadius: 8 }} />
            ) : (
              <div>
                <div style={{ fontSize: 32, marginBottom: 8 }}>📷</div>
                <div style={{ color: "#999" }}>点击上传参考照片（可选）</div>
              </div>
            )}
            <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }} onChange={handleFileSelect} />
          </div>

          {/* 文字描述 */}
          <textarea
            style={{ ...inputStyle, height: 60, resize: "none" }}
            placeholder="描述你想要的桌宠形象（如：一只橘色的小猫，戴着蝴蝶结）"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />

          {/* 风格选择 */}
          <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
            {styles.map((s) => (
              <button
                key={s.id}
                onClick={() => setStyle(s.id)}
                style={{
                  flex: 1,
                  padding: "8px 0",
                  borderRadius: 10,
                  border: style === s.id ? "2px solid #764ba2" : "2px solid #e0e0e0",
                  background: style === s.id ? "#f3e8ff" : "#fff",
                  cursor: "pointer",
                  fontSize: 13,
                }}
              >
                <div>{s.emoji}</div>
                <div>{s.label}</div>
              </button>
            ))}
          </div>

          <div style={{ marginTop: 20, display: "flex", justifyContent: "space-between" }}>
            <button
              style={{ ...btnStyle, background: "#e0e0e0", color: "#666" }}
              onClick={() => setStep("name")}
            >
              ← 上一步
            </button>
            <button style={btnStyle} onClick={handleGenerate}>
              🎨 生成形象
            </button>
          </div>
        </div>
      )}

      {/* Step 3: 生成中 */}
      {step === "generating" && (
        <div style={{ textAlign: "center", padding: 40 }}>
          <div style={{ fontSize: 48, marginBottom: 16, animation: "spin 1s linear infinite" }}>✨</div>
          <h3>正在生成 {petName || "桌宠"} 的形象...</h3>
          <p style={{ color: "#888", marginTop: 8 }}>这可能需要几秒钟</p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* Step 4: 完成 */}
      {step === "done" && (
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 64, marginBottom: 16 }}>🎉</div>
          <h2 style={{ margin: "0 0 8px" }}>{petName || "小宠"} 诞生了！</h2>
          <p style={{ color: "#888", margin: "0 0 24px" }}>你的桌宠已准备就绪</p>
          <button style={btnStyle} onClick={onComplete}>
            开始互动 🐾
          </button>
        </div>
      )}
    </div>
  );
};
