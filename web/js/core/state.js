// Shared state of the lesson player.
export const state = {
  lessons: [],   // localized lessons from /api/lessons
  tabs: [],      // [{id, hidden?}]
  cur: 0,        // index into lessons
  curTab: 'learn',
};
