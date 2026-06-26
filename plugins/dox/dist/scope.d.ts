import { Config } from "./config.js";
/** True if any path component of rel is an excluded name. */
export declare function isExcluded(rel: string, cfg: Config): boolean;
/** True if the directory directly contains a recognised code file. */
export declare function dirHasCode(d: string, cfg: Config): boolean;
/** Sorted absolute paths of the code files directly inside d. */
export declare function codeFiles(d: string, cfg: Config): string[];
/** A folder opts into per-file docs by placing the marker in its doc. */
export declare function isPerfileDir(d: string, cfg: Config): boolean;
/**
 * Every in-scope directory under the include roots, top-down.
 * In-scope = directly contains code, or already has a doc. The root is always
 * in scope so there is a top of the tree. Excluded dirs are never descended.
 */
export declare function scopeDirs(root: string, cfg: Config): string[];
/** True if any descendant of d (not d itself) has code or a doc. */
export declare function hasScopedDescendant(d: string, root: string, cfg: Config): boolean;
