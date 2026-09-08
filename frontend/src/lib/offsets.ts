import type { Node as PMNode } from "@tiptap/pm/model";

export function plainTextFromDoc(doc: PMNode): string {
  const parts: string[] = [];
  doc.forEach((block) => {
    parts.push(block.textContent);
  });
  return parts.join("\n");
}

export function mapRange(
  doc: PMNode,
  start: number,
  end: number,
): { from: number; to: number } | null {
  let index = 0;
  let from: number | null = null;
  let to: number | null = null;
  let blockIndex = 0;

  doc.forEach((block, blockPos) => {
    if (blockIndex > 0) {
      if (index === start) from = blockPos;
      if (index === end) to = blockPos;
      index += 1;
    }
    blockIndex += 1;
    block.descendants((node, posInBlock) => {
      if (!node.isText || !node.text) {
        return;
      }
      const abs = blockPos + 1 + posInBlock;
      for (let i = 0; i < node.text.length; i += 1) {
        if (index === start) from = abs + i;
        if (index + 1 === end) to = abs + i + 1;
        index += 1;
      }
    });
  });

  if (end === index && to === null) {
    to = doc.content.size;
  }
  if (from === null || to === null || from > to) {
    return null;
  }
  return { from, to };
}
