#!/usr/bin/env node
// dox - deterministic AGENTS.md tree engine (CLI entry point).
//
// A hierarchy of AGENTS.md files acts as a map of a codebase so a coding agent
// loads only the docs relevant to the path it is touching, instead of the whole
// repo. DOX (the original) is a prompt that asks the model to maintain this by
// hand. This is the mechanistic version: the structure and the index are derived
// from the filesystem, drift is detected by this tool, and the model is only ever
// asked to write prose - and only when this tool says it must.
//
// Jobs and who does them:
//   J1 load the right docs for a path   -> `dox context`  (deterministic)
//   J2 keep the structural index right  -> `dox sync`     (deterministic)
//   J3 keep the prose right             -> the agent, when `dox check` flags it
//
// Exit codes: 0 clean, 1 hard drift, 2 usage error.
import { resolve } from "node:path";
import { die, findRoot, loadConfig } from "./config.js";
import { Args, cmdCheck, cmdContext, cmdInit, cmdSync } from "./commands.js";

const USAGE = `dox - deterministic AGENTS.md tree engine

usage: dox [-C DIR] <command> [options]

commands:
  init [--scaffold]   scaffold .dox.json + root AGENTS.md (+ a stub per folder)
  sync                regenerate the Child Docs Index in every AGENTS.md
  check [--strict]    report drift (missing/stale/dangling/sections/per-file/prose)
  context <path>      print the root->path AGENTS.md chain (used by hooks and agents)
`;

function main(argv: string[]): number {
  let chdir = ".";
  const rest: string[] = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "-C") {
      chdir = argv[++i] ?? die("-C requires a directory");
    } else if (a === "-h" || a === "--help") {
      process.stdout.write(USAGE);
      return 0;
    } else {
      rest.push(a);
    }
  }

  const cmd = rest.shift();
  if (!cmd) {
    process.stderr.write(USAGE);
    return 2;
  }

  const args: Args = {};
  for (const a of rest) {
    if (a === "--scaffold") args.scaffold = true;
    else if (a === "--strict") args.strict = true;
    else if (!a.startsWith("-") && args.path === undefined) args.path = a;
    else die(`unknown argument: ${a}`);
  }

  const root = findRoot(resolve(chdir));
  const cfg = loadConfig(root);

  switch (cmd) {
    case "init":
      return cmdInit(root, cfg, args);
    case "sync":
      return cmdSync(root, cfg);
    case "check":
      return cmdCheck(root, cfg, args);
    case "context":
      if (!args.path) die("context requires a path");
      return cmdContext(root, cfg, args);
    default:
      return die(`unknown command: ${cmd}`);
  }
}

process.exit(main(process.argv.slice(2)));
