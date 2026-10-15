import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

/**
 * Black (default) / light theme.
 *
 * The theme is just a `data-theme` attribute on <html>; every colour in the app
 * is a CSS variable remapped by that attribute in src/styles/tokens.css. The
 * initial value is applied by an inline script in index.html BEFORE React
 * loads, so this provider only has to read it back and keep it in sync.
 *
 * Storage is a per-viewer convenience: if localStorage is unavailable the
 * theme simply follows the operating system preference.
 */
export type Theme = 'light' | 'dark';

const STORAGE_KEY = 'indusbrain.theme';

function readInitialTheme(): Theme {
  const attr = document.documentElement.getAttribute('data-theme');
  if (attr === 'light' || attr === 'dark') return attr;
  return 'dark'; // black is the default theme
}

const ThemeContext = createContext<{ theme: Theme; toggleTheme: () => void }>({
  theme: 'light',
  toggleTheme: () => {},
});

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setTheme] = useState<Theme>(readInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => {
      const next = current === 'dark' ? 'light' : 'dark';
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch {
        /* storage blocked — the choice just won't persist */
      }
      return next;
    });
  }, []);

  return <ThemeContext.Provider value={{ theme, toggleTheme }}>{children}</ThemeContext.Provider>;
};

export const useTheme = () => useContext(ThemeContext);
