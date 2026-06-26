export declare const DOC_NAME_DEFAULT = "AGENTS.md";
export declare const CONFIG_NAME = ".dox.json";
export declare const INDEX_OPEN = "<!-- dox:index -->";
export declare const INDEX_CLOSE = "<!-- /dox:index -->";
export declare const INDEX_HEADING = "## Child Docs Index";
export declare const PERFILE_MARKER = "<!-- dox:per-file -->";
export declare const SECTION_ALIASES: Record<string, string[]>;
export interface Config {
    doc_name: string;
    include: string[];
    required_sections: string[];
    enforce_sections: boolean;
    exclude: string[];
    code_exts: string[];
    require_docs_for_code_dirs: boolean;
}
export declare const DEFAULT_CONFIG: Config;
/** Exit with usage error (code 2) after printing to stderr. */
export declare function die(msg: string): never;
/** A path relative to root, always with forward slashes (stable across OSes). */
export declare function relPosix(root: string, p: string): string;
/** Nearest ancestor (inclusive) holding a .dox.json or .git; else start. */
export declare function findRoot(start: string): string;
export declare function loadConfig(root: string): Config;
