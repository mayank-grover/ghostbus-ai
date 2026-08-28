import React, { useState, useEffect, useRef } from 'react';
import { Search, X, MapPin, Loader2 } from 'lucide-react';
import { searchStops } from '../services/api';

export default function StopSearch({ onSelectStop, currentStop }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const [error, setError] = useState(null);
  
  const containerRef = useRef(null);

  // Debounced search logic
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setIsOpen(false);
      setIsSearching(false);
      setError(null);
      return;
    }

    setIsSearching(true);
    setError(null);

    const timer = setTimeout(async () => {
      try {
        const stops = await searchStops(query);
        setResults(stops);
        setIsOpen(true);
        setFocusedIndex(-1);
      } catch (err) {
        console.error('Stop search error:', err);
        setError('Failed to search stops');
        setResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [query]);

  // Click outside listener
  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (stop) => {
    setQuery(stop.stop_name);
    setIsOpen(false);
    setFocusedIndex(-1);
    onSelectStop(stop);
  };

  const handleClear = () => {
    setQuery('');
    setResults([]);
    setIsOpen(false);
    setFocusedIndex(-1);
  };

  const handleKeyDown = (e) => {
    if (!isOpen || results.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setFocusedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setFocusedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (focusedIndex >= 0 && focusedIndex < results.length) {
        handleSelect(results[focusedIndex]);
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  return (
    <div className="search-wrapper" ref={containerRef}>
      <div className="search-input-box">
        <Search className="search-icon" size={20} />
        
        <input
          type="text"
          className="search-input"
          placeholder="Search your bus stop (e.g. Slussen, T-Centralen)..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            if (results.length > 0) setIsOpen(true);
          }}
          onKeyDown={handleKeyDown}
        />

        {isSearching && (
          <Loader2 className="search-icon spinner" style={{ left: 'auto', right: '3rem' }} size={18} />
        )}

        {query && (
          <button
            type="button"
            className="clear-btn"
            onClick={handleClear}
            aria-label="Clear search"
          >
            <X size={18} />
          </button>
        )}
      </div>

      {isOpen && (
        <div className="search-dropdown glass-panel">
          {results.length > 0 ? (
            results.map((stop, idx) => (
              <button
                key={stop.stop_id}
                type="button"
                className={`dropdown-item ${idx === focusedIndex ? 'focused' : ''}`}
                onClick={() => handleSelect(stop)}
                onMouseEnter={() => setFocusedIndex(idx)}
              >
                <div className="stop-info">
                  <span className="stop-name">{stop.stop_name}</span>
                  <span className="stop-sub">Stop #{stop.stop_id}</span>
                </div>
                <MapPin size={16} className="text-muted" style={{ color: 'var(--text-muted)' }} />
              </button>
            ))
          ) : (
            !isSearching && (
              <div style={{ padding: '0.85rem 1rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                No matching bus stops found.
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}
