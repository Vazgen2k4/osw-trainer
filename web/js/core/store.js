// localStorage wrapper: values are JSON; private windows or blocked storage silently fall back to defaults.
export const store = {
  get(key, fallback) {
    try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback } catch (e) { return fallback }
  },
  set(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)) } catch (e) {}
  },
};
