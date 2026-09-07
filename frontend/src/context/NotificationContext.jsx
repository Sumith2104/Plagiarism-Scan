import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { X, CheckCircle2, AlertCircle, Info, AlertTriangle } from 'lucide-react';

const NotificationContext = createContext(null);

let idCounter = 0;

export function NotificationProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  // Request browser desktop notification permission on demand
  const requestDesktopPermission = useCallback(async () => {
    if (typeof window !== 'undefined' && 'Notification' in window) {
      if (window.Notification.permission === 'default') {
        try {
          await window.Notification.requestPermission();
        } catch (e) {
          console.warn('Notification permission error:', e);
        }
      }
    }
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (type, title, message, duration = 4500) => {
      const id = ++idCounter;
      const newToast = { id, type, title, message, duration, createdAt: Date.now() };

      setToasts((prev) => [newToast, ...prev.slice(0, 4)]); // Keep max 5 visible

      // Trigger desktop notification if permitted
      if (
        typeof window !== 'undefined' &&
        'Notification' in window &&
        window.Notification.permission === 'granted'
      ) {
        try {
          new window.Notification(title, {
            body: message,
            icon: '/logo-icon.png',
            badge: '/logo-icon.png',
          });
        } catch (e) {
          console.warn('Desktop notification failed:', e);
        }
      }

      if (duration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, duration);
      }

      return id;
    },
    [removeToast]
  );

  const notify = {
    success: (title, message, duration) => addToast('success', title, message, duration),
    error: (title, message, duration) => addToast('error', title, message, duration),
    info: (title, message, duration) => addToast('info', title, message, duration),
    warning: (title, message, duration) => addToast('warning', title, message, duration),
    requestPermission: requestDesktopPermission,
  };

  return (
    <NotificationContext.Provider value={notify}>
      {children}
      {/* Toast Notification Container */}
      <div
        className="fixed top-5 right-5 z-50 flex flex-col gap-3 max-w-sm sm:max-w-md w-full pointer-events-none px-4 sm:px-0"
        aria-live="polite"
      >
        {toasts.map((toast) => (
          <ToastCard key={toast.id} toast={toast} onDismiss={() => removeToast(toast.id)} />
        ))}
      </div>
    </NotificationContext.Provider>
  );
}

function ToastCard({ toast, onDismiss }) {
  const [progress, setProgress] = useState(100);

  useEffect(() => {
    if (!toast.duration || toast.duration <= 0) return;
    const interval = 50;
    const step = (interval / toast.duration) * 100;
    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev <= step) {
          clearInterval(timer);
          return 0;
        }
        return prev - step;
      });
    }, interval);

    return () => clearInterval(timer);
  }, [toast.duration]);

  const typeConfig = {
    success: {
      border: 'border-emerald-500/30 bg-white/95 dark:bg-slate-900/95 shadow-emerald-500/10',
      bar: 'bg-emerald-500',
      badge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      icon: <CheckCircle2 className="w-4 h-4 text-emerald-600" />,
      ring: 'ring-emerald-500/20',
    },
    error: {
      border: 'border-rose-500/30 bg-white/95 dark:bg-slate-900/95 shadow-rose-500/10',
      bar: 'bg-rose-500',
      badge: 'bg-rose-50 text-rose-700 border-rose-200',
      icon: <AlertCircle className="w-4 h-4 text-rose-600" />,
      ring: 'ring-rose-500/20',
    },
    warning: {
      border: 'border-amber-500/30 bg-white/95 dark:bg-slate-900/95 shadow-amber-500/10',
      bar: 'bg-amber-500',
      badge: 'bg-amber-50 text-amber-700 border-amber-200',
      icon: <AlertTriangle className="w-4 h-4 text-amber-600" />,
      ring: 'ring-amber-500/20',
    },
    info: {
      border: 'border-indigo-500/30 bg-white/95 dark:bg-slate-900/95 shadow-indigo-500/10',
      bar: 'bg-indigo-500',
      badge: 'bg-indigo-50 text-indigo-700 border-indigo-200',
      icon: <Info className="w-4 h-4 text-indigo-600" />,
      ring: 'ring-indigo-500/20',
    },
  };

  const currentConfig = typeConfig[toast.type] || typeConfig.info;

  return (
    <div
      className={`pointer-events-auto relative overflow-hidden rounded-2xl border backdrop-blur-xl shadow-2xl transition-all duration-300 animate-slide-in ${currentConfig.border}`}
      style={{ minWidth: '320px' }}
    >
      <div className="p-4 flex items-start gap-3.5">
        {/* Custom Logo from images folder */}
        <div className="relative flex-shrink-0">
          <div className={`w-11 h-11 rounded-xl bg-white p-0.5 shadow-md border border-gray-100 flex items-center justify-center overflow-hidden ring-2 ${currentConfig.ring}`}>
            <img
              src="/logo-icon.png"
              alt="PlagiaScan Logo"
              className="w-full h-full object-contain"
              onError={(e) => {
                e.target.src = '/logo.png';
              }}
            />
          </div>
          <span className="absolute -bottom-1 -right-1 rounded-full bg-white p-0.5 shadow">
            {currentConfig.icon}
          </span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 pr-1">
          <div className="flex items-center justify-between gap-2 mb-0.5">
            <h4 className="text-sm font-bold text-slate-800 dark:text-slate-100 truncate">
              {toast.title}
            </h4>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full border bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              PlagiaScan
            </span>
          </div>
          {toast.message && (
            <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-3 leading-relaxed">
              {toast.message}
            </p>
          )}
        </div>

        {/* Dismiss Button */}
        <button
          onClick={onDismiss}
          className="flex-shrink-0 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg p-1 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          aria-label="Dismiss notification"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Progress Bar */}
      {toast.duration > 0 && (
        <div className="w-full bg-gray-100 dark:bg-slate-800 h-1 overflow-hidden">
          <div
            className={`h-full transition-all duration-75 ease-linear ${currentConfig.bar}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
}

export function useNotification() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return context;
}
