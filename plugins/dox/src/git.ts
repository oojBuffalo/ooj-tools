// Reads the set of changed files from git (working tree + index). Used only to
// flag prose drift (code changed, its doc did not) - a warning, never a gate.
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";

/** Files changed in the working tree + index, as paths relative to root. */
export function gitChanged(root: string): Set<string> {
  const out = new Set<string>();
  if (!existsSync(join(root, ".git"))) return out;
  for (const args of [["diff", "--name-only"], ["diff", "--name-only", "--cached"]]) {
    let stdout: string;
    try {
      stdout = execFileSync("git", args, { cwd: root, encoding: "utf8" });
    } catch {
      return new Set();
    }
    for (const line of stdout.split(/\r?\n/)) {
      const t = line.trim();
      if (t) out.add(t);
    }
  }
  return out;
}
