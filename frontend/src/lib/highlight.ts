import { Extension } from "@tiptap/core";
import type { Editor } from "@tiptap/react";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";

import { mapRange } from "@/lib/offsets";
import type { Correction } from "@/lib/types";

const key = new PluginKey("issueHighlights");

type HighlightMeta = { issues: Correction[]; activeId?: string | null };

function decorationsFor(
  doc: Parameters<typeof mapRange>[0],
  issues: Correction[],
  activeId?: string | null,
) {
  const widgets: Decoration[] = [];
  for (const issue of issues) {
    const range = mapRange(doc, issue.start, issue.end);
    if (!range || range.from === range.to) continue;
    const on = issue.id === activeId ? " mw-mark-on" : "";
    widgets.push(
      Decoration.inline(range.from, range.to, {
        class: `mw-mark mw-mark-${issue.severity}${on}`,
        "data-issue-id": issue.id,
      }),
    );
  }
  return DecorationSet.create(doc, widgets);
}

export const IssueHighlight = Extension.create<{ issues: Correction[] }>({
  name: "issueHighlight",
  addOptions() {
    return { issues: [] };
  },
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key,
        state: {
          init: (_, state) => decorationsFor(state.doc, this.options.issues),
          apply: (tr, old) => {
            const next = tr.getMeta(key) as HighlightMeta | Correction[] | undefined;
            if (Array.isArray(next)) {
              return decorationsFor(tr.doc, next);
            }
            if (next?.issues) {
              return decorationsFor(tr.doc, next.issues, next.activeId);
            }
            if (tr.docChanged) {
              return old.map(tr.mapping, tr.doc);
            }
            return old;
          },
        },
        props: {
          decorations(state) {
            return key.getState(state) as DecorationSet;
          },
          handleDOMEvents: {
            click(_view, event) {
              const target = event.target;
              if (!(target instanceof Element)) return false;
              const mark = target.closest("[data-issue-id]");
              const id = mark?.getAttribute("data-issue-id");
              if (!id) return false;
              window.dispatchEvent(new CustomEvent("mw-select-issue", { detail: id }));
              return true;
            },
          },
        },
      }),
    ];
  },
});

export function setIssueDecorations(
  editor: Editor,
  issues: Correction[],
  activeId?: string | null,
) {
  editor.view.dispatch(editor.state.tr.setMeta(key, { issues, activeId }));
}
