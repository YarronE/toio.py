// Electron Preload — 安全暴露 API 给渲染进程

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  // 设置鼠标穿透
  setIgnoreMouse: (ignore) => ipcRenderer.send("set-ignore-mouse", ignore),

  // 获取屏幕尺寸
  getScreenSize: () => ipcRenderer.invoke("get-screen-size"),
});
