// Finds dangling local links in a doc's prose (index links are machine-owned
// and verified by sync, so they are skipped here).
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { INDEX_CLOSE, INDEX_OPEN } from "./config.js";

const LINK_RE = /\[[^\]]*\]\(([^)]+)\)/g;

export function danglingRefs(docPath: string): string[] {
  const bad: string[] = [];
  const base = dirname(docPath);
  let inIndex = false;
  for (const raw of readFileSync(docPath, "utf8").split(/\r?\n/)) {
    const s = raw.trim();
    if (s === INDEX_OPEN) { inIndex = true; continue; }
    if (s === INDEX_CLOSE) { inIndex = false; continue; }
    if (inIndex) continue;
    LINK_RE.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = LINK_RE.exec(raw)) !== null) {
      const target = m[1].split("#")[0].trim();
      if (!target || /^(https?:\/\/|mailto:)/.test(target)) continue;
      if (!existsSync(join(base, target))) bad.push(target);
    }
  }
  return bad;
}
