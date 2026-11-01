// Entry point: wires the features together and owns the "current language" flow.
import { api } from './core/api.js';
import { onAction, listen } from './core/actions.js';
import { loadStrings, t, lang } from './core/i18n.js';
import { state } from './core/state.js';
import { store } from './core/store.js';
import { renderThemeButton, toggleTheme } from './features/theme/theme.js';
import { progress } from './features/progress/progress.js';
import { renderSwitcher } from './features/languages/switcher.js';
import { openLanguageDialog, downloadTemplate, copyPrompt, chooseFiles, removeLanguage } from './features/languages/dialog.js';
import { renderSide, setSideTab, copyCode, toggleSide, toggleNav, restorePanels } from './features/sidebar/sidebar.js';
import { show, goTab } from './features/lessons/view.js';
import { visibleTabs } from './features/lessons/nav.js';
import { run, hint, solution, resetDraft } from './features/lessons/runner.js';

let locales = [];

function renderToolbar() {
  const tg = document.getElementById('tg');
  tg.textContent = t('ui_menu'); tg.title = t('ui_menuT');
  const tg2 = document.getElementById('tg2');
  tg2.textContent = t('ui_pfx'); tg2.title = t('ui_pfxT');
  renderThemeButton();
  renderSwitcher(locales, { onSelect: setLang, onAdd: openDialog });
}

const dialogContext = () => ({ locales, tabs: visibleTabs(), onChanged: languagesChanged });
const openDialog = () => openLanguageDialog(dialogContext());

async function languagesChanged(added, removed) {
  locales = await api.locales();
  if (added) await setLang(added);
  else if (removed && removed === lang) await setLang('en');
  else renderToolbar();
  return dialogContext();
}

async function setLang(code) {
  const actual = await loadStrings(code);
  store.set('osw_lang', actual);
  const data = await api.lessons(actual);
  state.lessons = data.lessons;
  state.tabs = data.tabs;
  renderToolbar();
  renderSide();
  show(Math.min(state.cur, state.lessons.length - 1));
}

function resetAll() {
  if (!confirm(t('ui_confirmResetAll'))) return;
  progress.clear();
  show(0);
}

const handlers = {
  'toggle-nav': toggleNav,
  'toggle-side': toggleSide,
  'toggle-theme': toggleTheme,
  'go-tab': el => goTab(el.dataset.arg),
  'show': el => show(Number(el.dataset.arg)),
  'reset-all': resetAll,
  'run': run,
  'hint': hint,
  'solution': solution,
  'reset': resetDraft,
  'side-tab': el => setSideTab(el.dataset.arg),
  'copy': copyCode,
  'lang-download': downloadTemplate,
  'lang-prompt': copyPrompt,
  'lang-upload': chooseFiles,
  'lang-remove': removeLanguage,
};

async function init() {
  Object.entries(handlers).forEach(([name, fn]) => onAction(name, fn));
  listen();
  restorePanels();
  locales = await api.locales();
  state.cur = progress.lastIndex();
  await setLang(initialLanguage());
}

// the saved choice, else the browser's language if we have it, else English
function initialLanguage() {
  const have = code => locales.some(x => x.code === code);
  const saved = store.get('osw_lang', null);
  if (saved && have(saved)) return saved;
  const browser = (navigator.languages || [navigator.language || '']).map(x => x.toLowerCase());
  return browser.flatMap(x => [x, x.split('-')[0]]).find(have) || 'en';
}

init();
