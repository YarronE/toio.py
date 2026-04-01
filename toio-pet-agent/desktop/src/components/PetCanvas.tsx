import React, { useEffect, useRef } from "react";

interface PetCanvasProps {
  mood: string;
  isPhysical: boolean;
}

/**
 * 桌宠画布组件
 *
 * 使用 Canvas 渲染桌宠精灵动画。
 * 后续替换为 PixiJS 实现更丰富的精灵表动画。
 */
export const PetCanvas: React.FC<PetCanvasProps> = ({ mood, isPhysical }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const PET_SIZE = 128;

  // 情绪对应颜色 (临时占位，后续用精灵图替换)
  const moodColors: Record<string, string> = {
    happy: "#FFD700",
    excited: "#FF6B6B",
    calm: "#87CEEB",
    curious: "#9B59B6",
    sleepy: "#A0A0C0",
    sad: "#5DADE2",
    playful: "#2ECC71",
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animFrame = 0;
    const color = moodColors[mood] || "#87CEEB";

    const draw = () => {
      ctx.clearRect(0, 0, PET_SIZE, PET_SIZE);

      // 物理世界时显示为半透明 (实体在 toio 上)
      ctx.globalAlpha = isPhysical ? 0.3 : 1.0;

      // 身体 (圆形)
      const bounce = Math.sin(animFrame * 0.05) * 3;
      ctx.beginPath();
      ctx.arc(PET_SIZE / 2, PET_SIZE / 2 + bounce, PET_SIZE * 0.35, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = "#333";
      ctx.lineWidth = 2;
      ctx.stroke();

      // 眼睛
      const eyeY = PET_SIZE / 2 - 8 + bounce;
      ctx.fillStyle = "#333";
      ctx.beginPath();
      ctx.arc(PET_SIZE / 2 - 12, eyeY, 4, 0, Math.PI * 2);
      ctx.arc(PET_SIZE / 2 + 12, eyeY, 4, 0, Math.PI * 2);
      ctx.fill();

      // 嘴巴 (根据情绪)
      ctx.beginPath();
      const mouthY = PET_SIZE / 2 + 10 + bounce;
      if (mood === "happy" || mood === "excited" || mood === "playful") {
        ctx.arc(PET_SIZE / 2, mouthY, 8, 0, Math.PI); // 微笑
      } else if (mood === "sad") {
        ctx.arc(PET_SIZE / 2, mouthY + 8, 8, Math.PI, 0); // 哭脸
      } else if (mood === "sleepy") {
        ctx.moveTo(PET_SIZE / 2 - 6, mouthY);
        ctx.lineTo(PET_SIZE / 2 + 6, mouthY); // 平嘴
      } else {
        ctx.arc(PET_SIZE / 2, mouthY, 4, 0, Math.PI * 2); // 小圆嘴
      }
      ctx.strokeStyle = "#333";
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.globalAlpha = 1.0;
      animFrame++;
    };

    const interval = setInterval(draw, 1000 / 30); // 30 FPS
    return () => clearInterval(interval);
  }, [mood, isPhysical]);

  return (
    <canvas
      ref={canvasRef}
      width={PET_SIZE}
      height={PET_SIZE}
      style={{
        cursor: "pointer",
        imageRendering: "pixelated",
      }}
    />
  );
};
