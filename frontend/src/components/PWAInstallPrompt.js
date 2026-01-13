import { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { X, Download, Smartphone } from 'lucide-react';

export default function PWAInstallPrompt() {
  const [showPrompt, setShowPrompt] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [isIOS, setIsIOS] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);

  useEffect(() => {
    // Check if already installed
    if (window.matchMedia('(display-mode: standalone)').matches) {
      setIsInstalled(true);
      return;
    }

    // Check if iOS
    const iOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    setIsIOS(iOS);

    // Listen for beforeinstallprompt event (Android/Chrome)
    const handleBeforeInstall = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      
      // Check if user dismissed before
      const dismissed = localStorage.getItem('pwa-install-dismissed');
      if (!dismissed) {
        setTimeout(() => setShowPrompt(true), 3000); // Show after 3 seconds
      }
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstall);

    // Show iOS prompt after delay if not installed
    if (iOS && !localStorage.getItem('pwa-install-dismissed')) {
      setTimeout(() => setShowPrompt(true), 5000);
    }

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
    };
  }, []);

  const handleInstall = async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      
      if (outcome === 'accepted') {
        console.log('PWA installed');
        setIsInstalled(true);
      }
      
      setDeferredPrompt(null);
      setShowPrompt(false);
    }
  };

  const handleDismiss = () => {
    setShowPrompt(false);
    localStorage.setItem('pwa-install-dismissed', 'true');
  };

  if (isInstalled || !showPrompt) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 animate-in slide-in-from-bottom duration-300" dir="rtl">
      <div className="bg-gradient-to-r from-slate-900 to-slate-800 rounded-2xl shadow-2xl border border-slate-700 p-4 max-w-md mx-auto">
        <button 
          onClick={handleDismiss}
          className="absolute top-2 left-2 text-slate-400 hover:text-white p-1"
        >
          <X className="h-5 w-5" />
        </button>
        
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 bg-orange-500/20 rounded-xl p-3">
            <Smartphone className="h-8 w-8 text-orange-500" />
          </div>
          
          <div className="flex-1">
            <h3 className="font-bold text-white text-lg mb-1">
              تثبيت التطبيق
            </h3>
            <p className="text-slate-300 text-sm mb-3">
              {isIOS 
                ? 'اضغط على زر المشاركة ثم "إضافة إلى الشاشة الرئيسية"'
                : 'ثبّت التطبيق للوصول السريع والعمل بدون إنترنت'
              }
            </p>
            
            {!isIOS && (
              <Button 
                onClick={handleInstall}
                className="bg-orange-600 hover:bg-orange-700 text-white w-full"
              >
                <Download className="h-4 w-4 ml-2" />
                تثبيت الآن
              </Button>
            )}
            
            {isIOS && (
              <div className="bg-slate-700/50 rounded-lg p-3 text-sm text-slate-200">
                <div className="flex items-center gap-2 mb-2">
                  <span className="bg-blue-500 text-white px-2 py-0.5 rounded text-xs">1</span>
                  <span>اضغط على أيقونة المشاركة</span>
                  <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2L8 6h3v8h2V6h3L12 2zm-7 9v11h14V11h-2v9H7v-9H5z"/>
                  </svg>
                </div>
                <div className="flex items-center gap-2">
                  <span className="bg-blue-500 text-white px-2 py-0.5 rounded text-xs">2</span>
                  <span>اختر "إضافة إلى الشاشة الرئيسية"</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
