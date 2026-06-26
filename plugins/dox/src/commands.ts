// The four subcommands: init, sync, check, context. Each is deterministic
// except for the prose the agent writes, which check only gates indirectly.
import { existsSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { basename, dirname, extname, isAbsolute, join, resolve } from "node:path";
import { Config, CONFIG_NAME, DEFAULT_CONFIG, relPosix } from "./config.js";
import { codeFiles, dirHasCode, isPerfileDir, scopeDirs } from "./scope.js";
import { genIndex, replaceIndex } from "./indexgen.js";
import { sectionPresent } from "./summary.js";
import { danglingRefs } from "./links.js";
import { gitChanged } from "./git.js";
import { ROOT_TEMPLATE, stubTemplate } from "./templates.js";

export interface Args {
  scaffold?: boolean;
  strict?: boolean;
  path?: string;
}

export function cmdInit(root: string, cfg: Config, args: Args): number {
  const cfgp = join(root, CONFIG_NAME);
  if (!existsSync(cfgp)) {
    writeFileSync(cfgp, JSON.stringify(DEFAULT_CONFIG, null, 2) + "\n");
    console.log(`wrote ${CONFIG_NAME}`);
  }
  const doc = cfg.doc_name;
  let written = 0;
  const rootdoc = join(root, doc);
  if (!existsSync(rootdoc)) {
    writeFileSync(rootdoc, ROOT_TEMPLATE);
    written += 1;
  }
  if (args.scaffold) {
    // Stub a canonical-section doc in every in-scope folder, leaving prose (J3)
    // to the agent. Structure is deterministic; content is not.
    for (const d of scopeDirs(root, cfg)) {
      const dp = join(d, doc);
      if (existsSync(dp)) continue;
      writeFileSync(dp, stubTemplate(d === root ? "Project" : basename(d)));
      written += 1;
    }
  }
  const n = syncAll(root, cfg, true);
  console.log(
    `wrote ${written} doc stub(s), synced ${n}. ` +
      `Next: fill Purpose/contracts/etc. in each ${doc}, then \`dox check\`.` +
      (args.scaffold ? "" : "  (use `dox init --scaffold` to stub every folder)"),
  );
  return 0;
}

export function syncAll(root: string, cfg: Config, write: boolean): number {
  const doc = cfg.doc_name;
  let changed = 0;
  for (const d of scopeDirs(root, cfg)) {
    const dp = join(d, doc);
    if (!existsSync(dp)) continue;
    const old = readFileSync(dp, "utf8");
    const next = replaceIndex(old, genIndex(d, root, cfg));
    if (next !== old) {
      changed += 1;
      if (write) writeFileSync(dp, next);
    }
  }
  return changed;
}

export function cmdSync(root: string, cfg: Config): number {
  const n = syncAll(root, cfg, true);
  console.log(`dox: synced index in ${n} doc(s)`);
  return 0;
}

export function cmdCheck(root: string, cfg: Config, args: Args): number {
  const doc = cfg.doc_name;
  const hard: string[] = [];
  const warn: string[] = [];

  // missing docs for code-bearing dirs
  if (cfg.require_docs_for_code_dirs) {
    for (const d of scopeDirs(root, cfg)) {
      if ((dirHasCode(d, cfg) || d === root) && !existsSync(join(d, doc))) {
        hard.push(`MISSING   ${relPosix(root, d)}/ has code but no ${doc}`);
      }
    }
  }

  // stale index + dangling refs + required sections + per-file docs
  for (const d of scopeDirs(root, cfg)) {
    const dp = join(d, doc);
    if (!existsSync(dp)) continue;
    const text = readFileSync(dp, "utf8");
    const reld = relPosix(root, dp);
    if (replaceIndex(text, genIndex(d, root, cfg)) !== text) {
      hard.push(`STALE     ${reld} index out of date (run \`dox sync\`)`);
    }
    for (const ref of danglingRefs(dp)) {
      hard.push(`DANGLING  ${reld} -> ${ref} (missing)`);
    }
    if (cfg.enforce_sections !== false) {
      const missing = cfg.required_sections.filter((s) => !sectionPresent(text, s));
      if (missing.length) warn.push(`SECTIONS  ${reld} missing: ${missing.join(", ")}`);
    }
    // per-file documentation: a sibling <file>.md per source file
    if (isPerfileDir(d, cfg)) {
      for (const f of codeFiles(d, cfg)) {
        const name = basename(f);
        if (!existsSync(join(d, `${name}.md`))) {
          hard.push(`FILEDOC   ${relPosix(root, f)} has no sibling ${name}.md (folder is per-file)`);
        }
      }
    }
  }

  // prose drift: code in a dir changed but its doc did not (git only)
  const changed = gitChanged(root);
  if (changed.size) {
    const exts = new Set(cfg.code_exts);
    const touchedDocs = new Set([...changed].filter((c) => basename(c) === doc));
    const flagged = new Set<string>();
    for (const c of changed) {
      if (!exts.has(extname(c))) continue;
      const d = dirname(join(root, c));
      const relDoc = relPosix(root, join(d, doc));
      if (existsSync(join(d, doc)) && !touchedDocs.has(relDoc) && !flagged.has(relDoc)) {
        flagged.add(relDoc);
        warn.push(`PROSE?    ${relDoc} unchanged but code in ${relPosix(root, d)}/ changed`);
      }
    }
  }

  for (const w of warn) console.log(`dox: warn  ${w}`);
  for (const h of hard) console.log(`dox: ERROR ${h}`);

  if (hard.length) {
    console.log(`\ndox: ${hard.length} hard issue(s), ${warn.length} warning(s)`);
    return 1;
  }
  if (args.strict && warn.length) {
    console.log(`\ndox: ${warn.length} warning(s) (strict mode)`);
    return 1;
  }
  console.log(warn.length ? `dox: ok (${warn.length} warning(s))` : "dox: ok");
  return 0;
}

export function cmdContext(root: string, cfg: Config, args: Args): number {
  const doc = cfg.doc_name;
  let target = args.path as string;
  if (!isAbsolute(target)) target = join(process.cwd(), target);
  target = resolve(target);
  let base: string;
  try {
    base = statSync(target).isDirectory() ? target : dirname(target);
  } catch {
    base = dirname(target);
  }
  let rel = relPosix(root, base);
  if (rel.startsWith("..")) rel = ""; // outside the root
  const parts = !rel || rel === "." ? [] : rel.split("/").filter(Boolean);

  const chain: string[] = [];
  let cur = root;
  if (existsSync(join(cur, doc))) chain.push(join(cur, doc));
  for (const part of parts) {
    cur = join(cur, part);
    const dp = join(cur, doc);
    if (existsSync(dp)) chain.push(dp);
  }
  if (chain.length === 0) return 0;
  for (const dp of chain) {
    const body = readFileSync(dp, "utf8");
    console.log(`===== ${relPosix(root, dp)} =====`);
    console.log(body.replace(/\s+$/, ""));
    console.log("");
  }
  return 0;
}
