// Determines which directories are "in scope" for documentation and which
// files count as code. Pure functions of the filesystem - no model judgement.
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { extname, join, relative } from "node:path";
import { Config, PERFILE_MARKER } from "./config.js";

function isDir(p: string): boolean {
  try { return statSync(p).isDirectory(); } catch { return false; }
}

function isFile(p: string): boolean {
  try { return statSync(p).isFile(); } catch { return false; }
}

/** True if any path component of rel is an excluded name. */
export function isExcluded(rel: string, cfg: Config): boolean {
  if (!rel || rel === ".") return false;
  const parts = new Set(rel.split(/[\\/]/).filter((s) => s && s !== "."));
  return cfg.exclude.some((ex) => parts.has(ex));
}

/** True if the directory directly contains a recognised code file. */
export function dirHasCode(d: string, cfg: Config): boolean {
  const exts = new Set(cfg.code_exts);
  try {
    return readdirSync(d).some((name) => isFile(join(d, name)) && exts.has(extname(name)));
  } catch {
    return false;
  }
}

/** Sorted absolute paths of the code files directly inside d. */
export function codeFiles(d: string, cfg: Config): string[] {
  const exts = new Set(cfg.code_exts);
  try {
    return readdirSync(d)
      .filter((name) => isFile(join(d, name)) && exts.has(extname(name)))
      .sort()
      .map((name) => join(d, name));
  } catch {
    return [];
  }
}

/** A folder opts into per-file docs by placing the marker in its doc. */
export function isPerfileDir(d: string, cfg: Config): boolean {
  const dp = join(d, cfg.doc_name);
  try {
    return existsSync(dp) && readFileSync(dp, "utf8").includes(PERFILE_MARKER);
  } catch {
    return false;
  }
}

/**
 * Every in-scope directory under the include roots, top-down.
 * In-scope = directly contains code, or already has a doc. The root is always
 * in scope so there is a top of the tree. Excluded dirs are never descended.
 */
export function scopeDirs(root: string, cfg: Config): string[] {
  const doc = cfg.doc_name;
  const out: string[] = [];
  const seen = new Set<string>();

  const visit = (d: string): void => {
    if (seen.has(d)) return;
    if (d === root || dirHasCode(d, cfg) || existsSync(join(d, doc))) {
      seen.add(d);
      out.push(d);
    }
  };

  const walk = (d: string): void => {
    if (isExcluded(relative(root, d), cfg)) return;
    visit(d);
    let entries: string[];
    try { entries = readdirSync(d).sort(); } catch { return; }
    for (const name of entries) {
      const child = join(d, name);
      if (!isDir(child)) continue;
      if (isExcluded(relative(root, child), cfg)) continue;
      walk(child);
    }
  };

  for (const inc of cfg.include) {
    const base = inc === "." ? root : join(root, inc);
    if (existsSync(base)) walk(base);
  }
  return out;
}

/** True if any descendant of d (not d itself) has code or a doc. */
export function hasScopedDescendant(d: string, root: string, cfg: Config): boolean {
  let entries: string[];
  try { entries = readdirSync(d); } catch { return false; }
  for (const name of entries) {
    const child = join(d, name);
    if (!isDir(child)) continue;
    if (isExcluded(relative(root, child), cfg)) continue;
    if (dirHasCode(child, cfg) || existsSync(join(child, cfg.doc_name))) return true;
    if (hasScopedDescendant(child, root, cfg)) return true;
  }
  return false;
}
