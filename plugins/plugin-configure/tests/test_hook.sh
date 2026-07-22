#!/bin/bash
# Tests for hooks/session-start.sh. Run: bash plugins/plugin-configure/tests/test_hook.sh
set -u

HOOK="$(cd "$(dirname "$0")/.." && pwd)/hooks/session-start.sh"
fails=0

expect_silent() { # label dir
  out=$(cd "$2" && CLAUDE_PLUGIN_ROOT="/fake/plugin root" bash "$HOOK"; echo "rc=$?")
  if [ "$out" = "rc=0" ]; then echo "PASS: $1"; else echo "FAIL: $1 -> $out"; fails=$((fails + 1)); fi
}

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# 1. non-git dir -> silent, exit 0
mkdir "$tmp/plain"
expect_silent "non-git dir is silent" "$tmp/plain"

# 2. unconfigured git repo -> nudge mentioning the configure command
git init -q "$tmp/repo"
out=$(cd "$tmp/repo" && CLAUDE_PLUGIN_ROOT="/fake/plugin root" bash "$HOOK")
case "$out" in
  *hookSpecificOutput*plugin-configure:configure*) echo "PASS: unconfigured repo nudges" ;;
  *) echo "FAIL: unconfigured repo nudges -> $out"; fails=$((fails + 1)) ;;
esac

# 3. nudge output is valid JSON and carries the plugin root path
echo "$out" | python3 -c '
import json, sys
doc = json.load(sys.stdin)
ctx = doc["hookSpecificOutput"]["additionalContext"]
assert doc["hookSpecificOutput"]["hookEventName"] == "SessionStart", "wrong event"
assert "/fake/plugin root" in ctx, "plugin root missing from context"
' && echo "PASS: nudge is valid JSON with plugin root" || { echo "FAIL: nudge is valid JSON with plugin root"; fails=$((fails + 1)); }

# 3b. hostile plugin roots (double quote, backslash) still emit valid JSON
for weird in '/fake/pl"ug"in' '/fake/pl\ugin\root'; do
  out=$(cd "$tmp/repo" && CLAUDE_PLUGIN_ROOT="$weird" bash "$HOOK")
  if echo "$out" | python3 -c 'import json, sys; json.load(sys.stdin)' >/dev/null 2>&1; then
    echo "PASS: valid JSON for hostile root $weird"
  else
    echo "FAIL: valid JSON for hostile root $weird -> $out"; fails=$((fails + 1))
  fi
done

# 4. marker file -> silent
mkdir -p "$tmp/repo/.claude"
echo '{"skipped": true}' > "$tmp/repo/.claude/plugin-configure.json"
expect_silent "marker silences the hook" "$tmp/repo"
rm "$tmp/repo/.claude/plugin-configure.json"

# 5. existing skillOverrides -> silent (grandfathered hand-curated repo)
echo '{"skillOverrides": {"x": "off"}}' > "$tmp/repo/.claude/settings.local.json"
expect_silent "skillOverrides silences the hook" "$tmp/repo"

expect_nudge() { # label dir
  out=$(cd "$2" && CLAUDE_PLUGIN_ROOT="/fake/plugin root" bash "$HOOK"; echo "rc=$?")
  case "$out" in
    *hookSpecificOutput*"rc=0") echo "PASS: $1" ;;
    *) echo "FAIL: $1 -> $out"; fails=$((fails + 1)) ;;
  esac
}

# 6. "skillOverrides" as a string VALUE (not a key) -> still nudges
echo '{"permissions": {"deny": ["skillOverrides"]}}' > "$tmp/repo/.claude/settings.local.json"
expect_nudge "token as value does not silence" "$tmp/repo"

# 7. invalid JSON settings -> still nudges, no crash
echo '{not json' > "$tmp/repo/.claude/settings.local.json"
expect_nudge "invalid settings JSON does not silence" "$tmp/repo"
rm "$tmp/repo/.claude/settings.local.json"

# 8. project-scope .claude/settings.json with skillOverrides -> silent
echo '{"skillOverrides": {"x": "off"}}' > "$tmp/repo/.claude/settings.json"
expect_silent "project-scope skillOverrides silences the hook" "$tmp/repo"

# 9. pathological local file must not mask the curated project settings
python3 -c 'n = 100000; print("[" * n + "]" * n)' > "$tmp/repo/.claude/settings.local.json"
expect_silent "unparseable local file does not mask curated project settings" "$tmp/repo"
rm "$tmp/repo/.claude/settings.json"

# 10. BOM-prefixed curated settings -> still silent
printf '\xef\xbb\xbf{"skillOverrides": {"x": "off"}}' > "$tmp/repo/.claude/settings.local.json"
expect_silent "BOM-prefixed curated settings silences the hook" "$tmp/repo"
rm "$tmp/repo/.claude/settings.local.json"

# 11. FIFO at a settings path -> no hang, falls through to the nudge
mkfifo "$tmp/repo/.claude/settings.local.json"
expect_nudge "FIFO settings file does not hang the hook" "$tmp/repo"
rm "$tmp/repo/.claude/settings.local.json"

echo "---"
if [ "$fails" -eq 0 ]; then echo "ALL PASS"; else echo "$fails FAILURE(S)"; fi
exit "$fails"
