// Feature: progress — solved tasks and drafts, kept in this browser (same keys as the first version of the trainer).
import { store } from '../../core/store.js';

let done = store.get('osw_done', {});
let drafts = store.get('osw_drafts', {});

export const progress = {
  isDone: id => !!done[id],
  markDone(id) { done[id] = 1; store.set('osw_done', done) },
  unmark(id) { delete done[id]; store.set('osw_done', done) },
  draft: id => drafts[id],
  saveDraft(id, text) { drafts[id] = text; store.set('osw_drafts', drafts) },
  dropDraft(id) { delete drafts[id]; store.set('osw_drafts', drafts) },
  lastIndex: () => store.get('osw_cur', 0),
  setLastIndex: i => store.set('osw_cur', i),
  clear() {
    done = {}; drafts = {};
    store.set('osw_done', done); store.set('osw_drafts', drafts); store.set('osw_cur', 0);
  },
};
