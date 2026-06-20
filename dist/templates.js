// Canonical doc templates. The structure is deterministic; the prose is left
// for the agent (J3) to fill in.
import { DOC_NAME_DEFAULT, INDEX_CLOSE, INDEX_OPEN } from "./config.js";
export const ROOT_TEMPLATE = `<!-- Your own project/agent instructions stay above. The DOX framework is appended below. -->

# DOX framework

You maintain a hierarchy of ${DOC_NAME_DEFAULT} files coupled to the codebase - one per
folder - as a map of this repo. Each file documents a single domain and ends with a
Child Docs Index linking its subfolders.

- **Before editing** a path, read the ${DOC_NAME_DEFAULT} chain from the root down to it
  (\`dox context <path>\`). Higher files give broad rules; deeper files give specifics.
- **After a meaningful change**, update the affected ${DOC_NAME_DEFAULT}(s) - the closest one
  and any parent whose contract changed. \`dox sync\` regenerates the index blocks.
- Keep docs concise and current: stable contracts, not history. Delete stale content.
- Shared code in another branch of the tree may be linked from the index or a section.

## Purpose
What this repository is for (one line - this feeds the parent index).

## Ownership
Top-level. Owns repo-wide conventions.

## Local contracts (rules)
- Repo-wide rules an agent must not violate.

## Work guidance
- How to organize code, where things go.

## Test & verify
- How to test and verify changes.

${INDEX_OPEN}
${INDEX_CLOSE}
`;
export function stubTemplate(name) {
    return `# ${name}

## Purpose
What \`${name}/\` is for (one line - this feeds the parent index).

## Ownership
Parent package / who owns this domain.

## Local contracts (rules)
- Rules specific to this folder (e.g. "return typed results, no untyped maps").

## Work guidance
- How to work here, where to put things.

## Test & verify
- How to test and verify changes in this folder.

${INDEX_OPEN}
${INDEX_CLOSE}
`;
}
