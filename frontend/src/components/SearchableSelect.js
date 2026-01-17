import React, { useState, useRef, useEffect } from 'react';
import { Search, X, ChevronDown, Check, Package } from 'lucide-react';

/**
 * SearchableSelect - قائمة منسدلة قابلة للبحث
 * تدعم آلاف العناصر مع البحث الفوري
 */
export default function SearchableSelect({
  options = [],
  value,
  onChange,
  placeholder = "اختر...",
  searchPlaceholder = "ابحث...",
  displayKey = "name",
  valueKey = "id",
  renderOption,
  className = "",
  disabled = false,
  maxHeight = "250px",
  showPrice = false
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef(null);
  const inputRef = useRef(null);

  // Filter options based on search
  const filteredOptions = options.filter(opt => {
    const searchLower = search.toLowerCase();
    const name = typeof opt === 'string' ? opt : (opt[displayKey] || '');
    const supplier = opt.supplier_name || '';
    return name.toLowerCase().includes(searchLower) || supplier.toLowerCase().includes(searchLower);
  });

  // Get selected option display text
  const selectedOption = options.find(opt => {
    const optValue = typeof opt === 'string' ? opt : opt[valueKey];
    return optValue === value;
  });
  
  const displayText = selectedOption 
    ? (typeof selectedOption === 'string' ? selectedOption : selectedOption[displayKey])
    : null;

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Focus search input when opening
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const handleSelect = (opt) => {
    const optValue = typeof opt === 'string' ? opt : opt[valueKey];
    onChange(optValue, opt);
    setIsOpen(false);
    setSearch("");
  };

  const handleClear = (e) => {
    e.stopPropagation();
    onChange("", null);
    setSearch("");
  };

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {/* Selected value display / trigger */}
      <div
        onClick={() => !disabled && setIsOpen(!isOpen)}
        className={`
          flex items-center justify-between gap-2 px-3 py-2.5 border-2 rounded-xl cursor-pointer
          bg-white transition-all duration-200 text-sm
          ${isOpen ? 'border-orange-500 ring-2 ring-orange-100 shadow-md' : 'border-slate-200 hover:border-orange-300'}
          ${disabled ? 'opacity-50 cursor-not-allowed bg-slate-100' : ''}
        `}
      >
        <span className={`truncate ${displayText ? 'text-slate-800 font-medium' : 'text-slate-400'}`}>
          {displayText || placeholder}
        </span>
        <div className="flex items-center gap-1.5 shrink-0">
          {value && !disabled && (
            <X 
              className="w-5 h-5 text-slate-400 hover:text-red-500 p-0.5 hover:bg-red-50 rounded-full transition-colors" 
              onClick={handleClear}
            />
          )}
          <ChevronDown className={`w-5 h-5 text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180 text-orange-500' : ''}`} />
        </div>
      </div>

      {/* Dropdown - Full screen modal on both mobile and desktop */}
      {isOpen && (
        <>
          {/* Overlay */}
          <div className="fixed inset-0 bg-black/60 z-[9998]" onClick={() => setIsOpen(false)} />
          
          {/* Modal content - centered on screen */}
          <div className="
            fixed z-[9999] 
            inset-x-4 top-20 bottom-20
            md:inset-auto md:top-1/2 md:left-1/2 md:-translate-x-1/2 md:-translate-y-1/2
            md:w-[500px] md:max-w-[90vw] md:h-[70vh] md:max-h-[600px]
            bg-white rounded-2xl shadow-2xl overflow-hidden
            animate-in fade-in zoom-in-95 duration-200
            flex flex-col
          ">
            {/* Header with title and close button */}
            <div className="flex items-center justify-between p-4 bg-gradient-to-l from-orange-500 to-orange-600 text-white shrink-0">
              <h3 className="font-bold text-lg">اختر صنف من الكتالوج</h3>
              <button onClick={() => setIsOpen(false)} className="p-2 hover:bg-white/20 rounded-lg transition-colors">
                <X className="w-6 h-6" />
              </button>
            </div>
            
            {/* Search input */}
            <div className="p-4 bg-gradient-to-b from-slate-50 to-white border-b border-slate-200 shrink-0">
              <div className="relative">
                <Search className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-orange-500" />
                <input
                  ref={inputRef}
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={searchPlaceholder}
                  className="w-full pr-12 pl-4 py-4 text-base bg-white border-2 border-slate-200 rounded-xl focus:outline-none focus:border-orange-400 focus:ring-4 focus:ring-orange-100 transition-all"
                  autoFocus
                />
              </div>
              {options.length > 0 && (
                <p className="text-xs text-slate-500 mt-2 text-center">{filteredOptions.length} من {options.length} صنف</p>
              )}
            </div>

            {/* Options list */}
            <div className="overflow-y-auto flex-1">
              {filteredOptions.length === 0 ? (
                <div className="p-8 text-center">
                  <Package className="w-16 h-16 text-slate-300 mx-auto mb-3" />
                  <p className="text-slate-500 text-base">
                    {search ? `لا توجد نتائج لـ "${search}"` : (options.length === 0 ? 'جاري التحميل...' : 'ابدأ الكتابة للبحث')}
                  </p>
                </div>
              ) : (
                filteredOptions.slice(0, 100).map((opt, idx) => {
                const optValue = typeof opt === 'string' ? opt : opt[valueKey];
                const isSelected = optValue === value;
                
                return (
                  <div
                    key={optValue || idx}
                    onClick={() => handleSelect(opt)}
                    className={`
                      px-5 py-4 cursor-pointer text-base md:text-sm transition-all duration-150 border-b border-slate-100 last:border-b-0
                      ${isSelected 
                        ? 'bg-gradient-to-l from-orange-50 to-orange-100 border-r-4 border-r-orange-500' 
                        : 'hover:bg-slate-50 active:bg-orange-50'
                      }
                    `}
                  >
                    {renderOption ? renderOption(opt) : (
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <p className={`font-semibold text-base md:text-sm ${isSelected ? 'text-orange-700' : 'text-slate-800'}`}>
                            {typeof opt === 'string' ? opt : opt[displayKey]}
                          </p>
                          {opt.supplier_name && (
                            <p className="text-sm md:text-xs text-slate-500 truncate mt-1">
                              المورد: {opt.supplier_name}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-3 shrink-0">
                          {opt.price !== undefined && (
                            <span className={`text-base md:text-sm font-bold px-3 py-1.5 rounded-lg ${isSelected ? 'bg-orange-200 text-orange-700' : 'bg-green-100 text-green-700'}`}>
                              {opt.price?.toLocaleString()} ر.س
                            </span>
                          )}
                          {isSelected && (
                            <Check className="w-6 h-6 text-orange-600" />
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
            {filteredOptions.length > 100 && (
              <div className="p-4 text-center text-sm text-slate-500 bg-slate-50 border-t border-slate-100">
                يظهر 100 من {filteredOptions.length} نتيجة - استخدم البحث للتصفية
              </div>
            )}
          </div>
        </div>
        </>
      )}
    </div>
  );
}
