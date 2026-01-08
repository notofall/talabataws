import React, { useState, useRef, useEffect } from 'react';
import { Search, X, ChevronDown } from 'lucide-react';

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
  maxHeight = "250px"
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef(null);
  const inputRef = useRef(null);

  // Filter options based on search
  const filteredOptions = options.filter(opt => {
    const searchLower = search.toLowerCase();
    const name = typeof opt === 'string' ? opt : (opt[displayKey] || '');
    return name.toLowerCase().includes(searchLower);
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
          flex items-center justify-between gap-2 px-3 py-2 border rounded-lg cursor-pointer
          bg-white hover:border-orange-400 transition-colors text-sm
          ${isOpen ? 'border-orange-500 ring-2 ring-orange-100' : 'border-slate-300'}
          ${disabled ? 'opacity-50 cursor-not-allowed bg-slate-100' : ''}
        `}
      >
        <span className={displayText ? 'text-slate-800' : 'text-slate-400'}>
          {displayText || placeholder}
        </span>
        <div className="flex items-center gap-1">
          {value && !disabled && (
            <X 
              className="w-4 h-4 text-slate-400 hover:text-red-500" 
              onClick={handleClear}
            />
          )}
          <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </div>
      </div>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg overflow-hidden">
          {/* Search input */}
          <div className="p-2 border-b border-slate-100">
            <div className="relative">
              <Search className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                ref={inputRef}
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={searchPlaceholder}
                className="w-full pr-8 pl-3 py-2 text-sm border border-slate-200 rounded-md focus:outline-none focus:border-orange-400"
              />
            </div>
          </div>

          {/* Options list */}
          <div className="overflow-y-auto" style={{ maxHeight }}>
            {filteredOptions.length === 0 ? (
              <div className="p-4 text-center text-slate-500 text-sm">
                {search ? `لا توجد نتائج لـ "${search}"` : 'لا توجد خيارات'}
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
                      px-3 py-2 cursor-pointer text-sm transition-colors
                      ${isSelected ? 'bg-orange-50 text-orange-700' : 'hover:bg-slate-50'}
                    `}
                  >
                    {renderOption ? renderOption(opt) : (
                      typeof opt === 'string' ? opt : opt[displayKey]
                    )}
                  </div>
                );
              })
            )}
            {filteredOptions.length > 100 && (
              <div className="p-2 text-center text-xs text-slate-400 border-t">
                يظهر 100 من {filteredOptions.length} - استخدم البحث لتضييق النتائج
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
