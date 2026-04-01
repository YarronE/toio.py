// Electron 主进程 — 创建透明无边框桌宠窗口

const { app, BrowserWindow, screen, ipcMain } = require("electron");
const path = require("path");

const isDev = process.env.NODE_ENV !== "production";

let mainWindow = null;

function createWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  mainWindow = new BrowserWindow({
    width: width,
    height: height,
    x: 0,
    y: 0,
    transparent: true,          // 透明背景
    frame: false,               // 无边框
    alwaysOnTop: true,          // 始终最上层
    skipTaskbar: true,          // 不显示在任务栏
    hasShadow: false,
    resizable: false,
    focusable: false,           // 不抢焦点 (点击穿透)
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // 点击穿透 — 透明区域不拦截鼠标
  mainWindow.setIgnoreMouseEvents(true, { forward: true });

  if (isDev) {
    mainWindow.loadURL("http://localhost:5173");
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// 允许渲染进程切换鼠标穿透状态 (桌宠区域需要可交互)
ipcMain.on("set-ignore-mouse", (_event, ignore) => {
  if (mainWindow) {
    mainWindow.setIgnoreMouseEvents(ignore, { forward: true });
  }
});

// 获取屏幕尺寸
ipcMain.handle("get-screen-size", () => {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;
  return { width, height };
});

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
