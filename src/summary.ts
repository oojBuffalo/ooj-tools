// Extracts a domain's one-line Purpose (for the parent index) and checks that
// the canonical sections are present.
import { existsSync, readFileSync } from "node:fs";
import { INDEX_CLOSE, INDEX_OPEN, SECTION_ALIASES } from "./config.js";

export function clip(s: string, n = 140): string {
  s = s.trim();
  return s.length <= n ? s : s.slice(0, n - 3) + "...";
}

/**
 * The one-line purpose of a doc, for the parent index. Prefers the Purpose
 * section text ('**Purpose** - ...' or a 'Purpose' heading's first line);
 * falls back to the first plain prose line. This is what propagates a domain's
 * purpose upward into its parent's Child Docs Index.
 */
export function summaryOf(docPath: string): string {
  if (!existsSync(docPath)) return "";
  const lines = readFileSync(docPath, "utf8").split(/\r?\n/);

  // 1) inline label: **Purpose** - text  |  **Purpose:** text
  for (const raw of lines) {
    const m = raw.match(/^\s*\*\*\s*purpose\s*\*\*\s*[:\-—]?\s*(.+)/i);
    if (m && m[1].trim()) return clip(m[1]);
  }
  // 2) a 'Purpose' heading, then the next prose line
  for (let i = 0; i < lines.length; i++) {
    if (/^\s*#+\s*purpose\b/i.test(lines[i])) {
      for (let j = i + 1; j < lines.length; j++) {
        const t = lines[j].trim();
        if (t && !t.startsWith("#") && !t.startsWith("<!--")) {
          return clip(t.replace(/^[-*>\s]+/, "").trim());
        }
      }
      break;
    }
  }
  // 3) fallback: first plain prose line outside the index block
  let inIndex = false;
  for (const raw of lines) {
    const line = raw.trim();
    if (line === INDEX_OPEN) { inIndex = true; continue; }
    if (line === INDEX_CLOSE) { inIndex = false; continue; }
    if (inIndex || !line) continue;
    if (/^[#\-*>`|]/.test(line) || line.startsWith("<!--")) continue;
    return clip(line);
  }
  return "";
}

/** True if the doc text contains any alias for the named canonical section. */
export function sectionPresent(text: string, name: string): boolean {
  const t = text.toLowerCase();
  const keys = SECTION_ALIASES[name] ?? [name.toLowerCase()];
  return keys.some((k) => t.includes(k));
}
