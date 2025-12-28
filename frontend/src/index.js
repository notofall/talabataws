import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

// Suppress ResizeObserver loop error (common with Radix UI components)
if (typeof window !== 'undefined') {
  // Suppress ResizeObserver errors completely
  const resizeObserverErr = window.ResizeObserver;
  window.ResizeObserver = class ResizeObserver extends resizeObserverErr {
    constructor(callback) {
      super((entries, observer) => {
        window.requestAnimationFrame(() => {
          callback(entries, observer);
        });
      });
    }
  };

  // Also suppress console errors for ResizeObserver
  const originalConsoleError = console.error;
  console.error = (...args) => {
    if (args[0]?.includes?.('ResizeObserver') || 
        (typeof args[0] === 'string' && args[0].includes('ResizeObserver'))) {
      return;
    }
    originalConsoleError.apply(console, args);
  };

  // Handle window errors
  window.addEventListener('error', (e) => {
    if (e.message?.includes('ResizeObserver')) {
      e.stopImmediatePropagation();
      e.preventDefault();
      return true;
    }
  });
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
