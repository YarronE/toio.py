/// <reference types="vite/client" />

interface ElectronAPI {
  setIgnoreMouse: (ignore: boolean) => void;
  getScreenSize: () => Promise<{ width: number; height: number }>;
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI;
  }
}

export {};
