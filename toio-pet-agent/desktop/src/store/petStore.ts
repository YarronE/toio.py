import { create } from "zustand";

const WS_URL = "ws://localhost:8765";
const API_URL = "http://localhost:8000";

interface PetState {
  name: string;
  mood: string;
  energy: number;
  affection: number;
  message: string;

  x: number;
  y: number;
  isPhysical: boolean;
  toioAngle: number;

  ws: WebSocket | null;
  connected: boolean;

  // 自主行为状态
  behaviorState: "idle" | "walking" | "sleeping" | "playing";
  walkTarget: { x: number; y: number } | null;

  // Actions
  connect: () => void;
  disconnect: () => void;
  sendChat: (msg: string) => void;
  updatePosition: (x: number, y: number) => void;
  setMood: (mood: string) => void;
  startBehaviorLoop: () => void;
}

export const usePetStore = create<PetState>((set, get) => ({
  name: "小宠",
  mood: "calm",
  energy: 100,
  affection: 50,
  message: "",
  x: 400,
  y: 500,
  isPhysical: false,
  toioAngle: 0,
  ws: null,
  connected: false,
  behaviorState: "idle",
  walkTarget: null,

  connect: () => {
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      set({ ws, connected: true });
      console.log("🐾 WS 已连接");
      // 启动自主行为循环
      get().startBehaviorLoop();
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const { type, data } = msg;

        switch (type) {
          case "chat_response":
            set({ message: data.text, mood: data.mood, energy: data.energy });
            break;

          case "state":
            set({ isPhysical: data.realm === "physical" });
            break;

          case "state_update":
            set({
              mood: data.mood ?? get().mood,
              energy: data.energy ?? get().energy,
            });
            break;

          case "transition":
            console.log("🔄 虚实过渡:", data);
            if (data.type === "virtual_to_physical") {
              set({ isPhysical: true, message: "我去物理世界溜达啦~ 🤖" });
            } else {
              set({ isPhysical: false, message: "我回来啦~ ✨" });
            }
            break;

          case "autonomous_action":
            handleAutonomousAction(data.action);
            break;

          case "pet_command":
            handlePetCommand(data);
            break;

          case "toio_position":
            set({ toioAngle: data.angle });
            break;
        }
      } catch (e) {
        console.error("WS 消息解析失败:", e);
      }
    };

    ws.onclose = () => {
      set({ ws: null, connected: false });
      console.log("🐾 WS 断开，3秒后重连...");
      setTimeout(() => get().connect(), 3000);
    };

    ws.onerror = () => {};
  },

  disconnect: () => {
    get().ws?.close();
    set({ ws: null, connected: false });
  },

  sendChat: (msg: string) => {
    const { ws, connected } = get();
    if (ws && connected) {
      ws.send(JSON.stringify({ type: "chat", data: { message: msg } }));
    }
  },

  updatePosition: (x: number, y: number) => {
    set({ x, y });
    const { ws, connected } = get();
    if (ws && connected) {
      ws.send(JSON.stringify({ type: "pet_position", data: { x, y } }));
    }
  },

  setMood: (mood: string) => set({ mood }),

  startBehaviorLoop: () => {
    // 桌宠自主漫步行为 (前端驱动)
    const loop = () => {
      const state = get();
      if (!state.connected || state.isPhysical) return;

      // 空闲时随机游走
      if (state.behaviorState === "idle" && Math.random() < 0.3) {
        const screenW = window.innerWidth || 1920;
        const screenH = window.innerHeight || 1080;
        const targetX = 100 + Math.random() * (screenW - 200);
        const targetY = 200 + Math.random() * (screenH - 300);
        set({ walkTarget: { x: targetX, y: targetY }, behaviorState: "walking" });
      }

      // 执行走路动画
      if (state.behaviorState === "walking" && state.walkTarget) {
        const dx = state.walkTarget.x - state.x;
        const dy = state.walkTarget.y - state.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 5) {
          set({ behaviorState: "idle", walkTarget: null });
        } else {
          const speed = 2;
          const nx = state.x + (dx / dist) * speed;
          const ny = state.y + (dy / dist) * speed;
          state.updatePosition(nx, ny);
        }
      }
    };

    setInterval(loop, 50); // 20 FPS 行为更新
  },
}));

// 处理后端下发的自主行为
function handleAutonomousAction(action: string) {
  const store = usePetStore.getState();
  switch (action) {
    case "idle_wander":
      store.setMood("curious");
      // 触发漫步
      const w = window.innerWidth || 1920;
      const h = window.innerHeight || 1080;
      usePetStore.setState({
        walkTarget: { x: 100 + Math.random() * (w - 200), y: 200 + Math.random() * (h - 300) },
        behaviorState: "walking",
      });
      break;
    case "idle_sit":
      store.setMood("calm");
      usePetStore.setState({ behaviorState: "idle" });
      break;
    case "idle_sleep":
      store.setMood("sleepy");
      usePetStore.setState({ behaviorState: "sleeping" });
      break;
  }
}

// 处理后端下发的桌宠指令
function handlePetCommand(data: any) {
  switch (data.action) {
    case "change_mood":
      usePetStore.setState({ mood: data.mood });
      break;
    case "walk_to":
      usePetStore.setState({
        walkTarget: { x: data.x, y: data.y },
        behaviorState: "walking",
      });
      break;
  }
}
