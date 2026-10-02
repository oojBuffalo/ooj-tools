---
name: popout
description: This skill should be used when the user asks to "pop out", "boop out", or "spin up" a super minimal app in the browser, or otherwise wants a throwaway local web page to view, compare, or edit some files or data side by side. In Codex, use when the user invokes $popout.
---

# Popout app

Build a **popout**: a throwaway, single-file local web app that puts the
user's files or data in a browser tab so they can look at them, compare them,
or edit them, then gets out of the way. Throwaway is the leading word: it
decides every choice below. The popout is a tool for this moment, not a
product. Ship the smallest thing that does exactly what the user asked for.

## Shape

- **One file, standard library only.** A Python script on `http.server`
  (`ThreadingHTTPServer`) with the HTML, CSS, and JS inlined as one string.
  No framework, no package install, no build step, no second file.
- **Loopback only.** Bind `127.0.0.1` and a fixed port (start at `8765`; pick
  the next one if `lsof -i :<port>` shows it taken).
- **Outside the repo.** Write the script to a scratch location, by default
  `~/.local/share/popout/<name>.py`, with a docstring that states how to
  run it. Put it in a repository only when the user asks to keep it there.
- **Minimal UI.** System fonts, a monospace `textarea` or `pre` per item, a
  thin header bar, CSS grid for side by side. Add only the controls the
  request names: a compare request gets a diff toggle (`difflib` on the
  server); an edit request gets a Save button and `⌘S`/`Ctrl+S`.
- **Quiet server.** Override `log_message` to stay silent, and send
  `Content-Length` with every response.

## Editing real files

When the popout can write, guard the write so the browser never clobbers a
change made elsewhere (by the user, another agent, or a concurrent session):

- Return a SHA-256 of the content with every read; the client sends it back
  on save.
- On save, re-hash the file on disk. If it differs, refuse with `409` and a
  message to reload; write only on a match.
- Show an "unsaved" marker while the editor differs from the last load, and
  reload the content from the server after each save.
- Write only the files the user named; hard-code their paths in the script
  rather than accepting a path from the client.

## Process

1. **Name the targets.** Resolve the exact files or data the user means
   (look them up; ask only if two candidates are equally plausible).
2. **Write the script** to the shape above.
3. **Start it in the background** so it keeps running after your turn
   (`python3 <script>` as a background command).
4. **Prove it is green** before you open it: `curl` each read endpoint, and
   for an editing popout, post a save with a bad hash and confirm the `409`
   left the file untouched.
5. **Open it**: `open http://127.0.0.1:<port>` on macOS, `xdg-open` on Linux.
6. **Report** the URL, what each pane and control does, the script path, the
   command to start it again, and that the server is still running. Stop the
   background server when the user is done with it.
