// The trainer's local JSON API. Writes carry X-Trainer so other web sites cannot trigger them.
async function request(method, url, body) {
  const init = { method, headers: {} };
  if (method !== 'GET') init.headers['X-Trainer'] = '1';
  if (body !== undefined) {
    init.body = typeof body === 'string' ? body : JSON.stringify(body);
    init.headers['Content-Type'] = typeof body === 'string' ? 'text/plain;charset=utf-8' : 'application/json';
  }
  const res = await fetch(url, init);
  const data = await res.json().catch(() => ({}));
  if (!res.ok && !data.error) data.error = `HTTP ${res.status}`;
  return data;
}

export const api = {
  locales: () => request('GET', '/api/locales'),
  strings: lang => request('GET', '/api/i18n?lang=' + encodeURIComponent(lang)),
  lessons: lang => request('GET', '/api/lessons?lang=' + encodeURIComponent(lang)),
  schema: () => request('GET', '/api/schema'),
  solution: id => request('GET', '/api/solution?id=' + id),
  run: (id, text, infer, lang) => request('POST', '/api/run', { id, text, infer, lang }),
  importPack: (text, params) => request('POST', '/api/locales?' + new URLSearchParams(params), text),
  removePack: (code, lang) => request('DELETE', `/api/locales/${encodeURIComponent(code)}?lang=${encodeURIComponent(lang)}`),
  templateUrl: params => '/api/locales/template?' + new URLSearchParams(params),
};
