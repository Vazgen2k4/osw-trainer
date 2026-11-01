// Feature: the code editor — a transparent <textarea> over a highlighted <pre> with line numbers.
import { highlight } from './highlight.js';

export function mountEditor({ textarea, mirror, onInput, onRun }) {
  const sync = () => {
    mirror.innerHTML = textarea.value.split('\n').map(x => '<div class="L">' + (x ? highlight(x) : ' ') + '</div>').join('');
  };
  sync();
  textarea.addEventListener('input', () => { onInput(textarea.value); sync() });
  textarea.addEventListener('keydown', e => {
    if (e.key === 'Tab') {
      e.preventDefault();
      textarea.setRangeText('  ', textarea.selectionStart, textarea.selectionEnd, 'end');
      textarea.dispatchEvent(new Event('input'));
    }
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); onRun() }
    if ((e.key === '/' || e.code === 'Slash') && (e.ctrlKey || e.metaKey)) { e.preventDefault(); toggleComment(textarea) }
  });
  return {
    get value() { return textarea.value },
    set value(v) { textarea.value = v; textarea.dispatchEvent(new Event('input')) },
  };
}

// Ctrl+/ (Cmd+/): comment / uncomment the selected lines with "#" (works in Turtle, SPARQL and RML)
function toggleComment(ed) {
  const v = ed.value;
  const a = v.lastIndexOf('\n', ed.selectionStart - 1) + 1;                 // start of the first selected line
  let bEnd = v.indexOf('\n', ed.selectionEnd > ed.selectionStart ? ed.selectionEnd - 1 : ed.selectionEnd);
  if (bEnd < 0) bEnd = v.length;                                              // end of the last selected line
  const lines = v.slice(a, bEnd).split('\n');
  const used = lines.filter(x => x.trim() !== '');
  const allCommented = used.length > 0 && used.every(x => /^\s*#/.test(x));
  let out;
  if (allCommented) out = lines.map(x => x.replace(/^(\s*)# ?/, '$1'));
  else {
    const k = used.length ? Math.min(...used.map(x => x.match(/^\s*/)[0].length)) : 0;
    out = lines.map(x => x.trim() === '' ? x : x.slice(0, k) + '# ' + x.slice(k));
  }
  const txt = out.join('\n');
  ed.focus();
  ed.setSelectionRange(a, bEnd);
  if (!document.execCommand || !document.execCommand('insertText', false, txt)) ed.setRangeText(txt, a, bEnd, 'select');   // execCommand keeps undo (Ctrl+Z)
  ed.setSelectionRange(a, a + txt.length);
  ed.dispatchEvent(new Event('input'));
}
