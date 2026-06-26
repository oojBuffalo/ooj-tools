// Constants, configuration, and repo-root discovery for the dox engine.
// Mirrors the deterministic contract: the structure and index are derived from
// the filesystem; only prose (J3) is ever model-written.
import { existsSync, readFileSync } from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";

export const DOC_NAME_DEFAULT = "AGENTS.md";
export const CONFIG_NAME = ".dox.json";
export const INDEX_OPEN = "<!-- dox:index -->";
export const INDEX_CLOSE = "<!-- /dox:index -->";
export const INDEX_HEADING = "## Child Docs Index";
export const PERFILE_MARKER = "<!-- dox:per-file -->";

// Canonical sections every domain doc carries, per the DOX video: purpose,
// ownership, local contracts (rules), work guidance, how to test and verify.
// Matched case-insensitively by the listed aliases so wording can vary.
export const SECTION_ALIASES: Record<string, string[]> = {
  "Purpose": ["purpose"],
  "Ownership": ["ownership", "parent"],
  "Local contracts": ["contract", "rules"],
  "Work guidance": ["guidance", "how to work"],
  "Test & verify": ["verify", "how to test"],
};

export interface Config {
  doc_name: string;
  include: string[];
  required_sections: string[];
  enforce_sections: boolean;
  exclude: string[];
  code_exts: string[];
  require_docs_for_code_dirs: boolean;
}

export const DEFAULT_CONFIG: Config = {
  doc_name: DOC_NAME_DEFAULT,
  include: ["."],
  required_sections: Object.keys(SECTION_ALIASES),
  enforce_sections: true,
  exclude: [
    ".git", "node_modules", "dist", "build", "out", "target",
    "__pycache__", ".venv", "venv", ".next", ".cache", "coverage",
  ],
  code_exts: [
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rs",
    ".java", ".kt", ".rb", ".php", ".c", ".cc", ".cpp", ".h", ".hpp",
    ".cs", ".swift", ".scala", ".sh", ".sql",
  ],
  require_docs_for_code_dirs: true,
};

/** Exit with usage error (code 2) after printing to stderr. */
export function die(msg: string): never {
  process.stderr.write(`dox: ${msg}\n`);
  process.exit(2);
}

/** A path relative to root, always with forward slashes (stable across OSes). */
export function relPosix(root: string, p: string): string {
  return relative(root, p).split(sep).join("/");
}

/** Nearest ancestor (inclusive) holding a .dox.json or .git; else start. */
export function findRoot(start: string): string {
  let dir = resolve(start);
  for (;;) {
    if (existsSync(join(dir, CONFIG_NAME)) || existsSync(join(dir, ".git"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return resolve(start);
}

export function loadConfig(root: string): Config {
  const cfg: Config = { ...DEFAULT_CONFIG };
  const p = join(root, CONFIG_NAME);
  if (existsSync(p)) {
    try {
      Object.assign(cfg, JSON.parse(readFileSync(p, "utf8")) as Partial<Config>);
    } catch (e) {
      die(`invalid ${CONFIG_NAME}: ${(e as Error).message}`);
    }
  }
  return cfg;
}
