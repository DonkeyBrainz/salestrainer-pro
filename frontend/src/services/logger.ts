
import { useState, useEffect } from 'react';

export type LogLevel = 'info' | 'warn' | 'error' | 'debug' | 'success';
export type LogCategory = 'System' | 'Gemini' | 'Audio' | 'Database' | 'UI' | 'Network' | 'Security';

export interface LogEntry {
  id: string;
  timestamp: Date;
  level: LogLevel;
  category: LogCategory;
  message: string;
  details?: any; // Structured object data
  stackTrace?: string;
}

const MAX_LOGS = 1000;
const logStore: LogEntry[] = [];
const listeners = new Set<(logs: LogEntry[]) => void>();

const notifyListeners = () => {
  // Return a copy to prevent mutation issues in UI
  listeners.forEach(listener => listener([...logStore]));
};

const internalLog = (level: LogLevel, category: LogCategory, message: string, details?: any) => {
  const entry: LogEntry = {
    id: Math.random().toString(36).substring(7),
    timestamp: new Date(),
    level,
    category,
    message,
    details: details ? JSON.parse(safeStringify(details)) : undefined, // Deep copy and safe serialize
  };

  // Capture stack trace for errors if not provided
  if (level === 'error' && !entry.stackTrace) {
     entry.stackTrace = new Error().stack;
  }

  logStore.push(entry);
  if (logStore.length > MAX_LOGS) {
    logStore.shift();
  }
  notifyListeners();

  // Mirror to actual console for backup
  // const style = 'font-weight: bold; color: #888;';
  // console.groupCollapsed(`%c[${category}] ${message}`, style);
  // if (details) console.dir(details);
  // console.groupEnd();
};

// Handle circular references
const safeStringify = (obj: any) => {
  const cache = new Set();
  return JSON.stringify(obj, (key, value) => {
    if (typeof value === 'object' && value !== null) {
      if (cache.has(value)) return '[Circular]';
      cache.add(value);
    }
    return value;
  });
};

let isInitialized = false;

export const initLogger = () => {
  if (isInitialized) return;
  isInitialized = true;

  // 1. Capture Global Exceptions
  window.onerror = (message, source, lineno, colno, error) => {
    internalLog('error', 'System', `Uncaught Exception: ${message}`, { source, lineno, colno, stack: error?.stack });
  };

  window.onunhandledrejection = (event) => {
    internalLog('error', 'System', `Unhandled Promise Rejection: ${event.reason}`, { reason: event.reason });
  };

  // 2. Intercept standard console logs (optional, strictly for external libs)
  // We prefer using the explicit 'logger' object below, but this catches loose logs
  const originalLog = console.log;
  console.log = (...args) => {
    // Try to detect if the first arg is a category tag we use, e.g. "[Audio]"
    let category: LogCategory = 'System';
    let msg = args.join(' ');

    // Heuristic: If we call console.log explicitly with an object
    internalLog('debug', category, msg, args.length > 1 ? args : undefined);
    originalLog.apply(console, args);
  };

  const originalError = console.error;
  console.error = (...args) => {
    internalLog('error', 'System', args.join(' '), args);
    originalError.apply(console, args);
  };

  logger.system('Logger initialized. Global error handlers active.');
};

// --- PUBLIC API ---

export const logger = {
  info: (category: LogCategory, message: string, details?: any) => internalLog('info', category, message, details),
  warn: (category: LogCategory, message: string, details?: any) => internalLog('warn', category, message, details),
  error: (category: LogCategory, message: string, details?: any) => internalLog('error', category, message, details),
  debug: (category: LogCategory, message: string, details?: any) => internalLog('debug', category, message, details),
  success: (category: LogCategory, message: string, details?: any) => internalLog('success', category, message, details),

  // Shortcuts
  system: (msg: string, data?: any) => internalLog('info', 'System', msg, data),
  gemini: (msg: string, data?: any) => internalLog('info', 'Gemini', msg, data),
  audio: (msg: string, data?: any) => internalLog('info', 'Audio', msg, data),
  db: (msg: string, data?: any) => internalLog('info', 'Database', msg, data),
  ui: (msg: string, data?: any) => internalLog('info', 'UI', msg, data),
};

export const useLogs = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);

  useEffect(() => {
    setLogs([...logStore]);
    const listener = (newLogs: LogEntry[]) => setLogs(newLogs);
    listeners.add(listener);
    return () => { listeners.delete(listener); };
  }, []);

  return {
    logs,
    clearLogs: () => {
      logStore.length = 0;
      notifyListeners();
    },
    exportLogs: () => {
        const blob = new Blob([JSON.stringify(logStore, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `salestrainer_logs_${new Date().toISOString()}.json`;
        a.click();
    }
  };
};
