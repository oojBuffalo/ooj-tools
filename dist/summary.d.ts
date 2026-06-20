export declare function clip(s: string, n?: number): string;
/**
 * The one-line purpose of a doc, for the parent index. Prefers the Purpose
 * section text ('**Purpose** - ...' or a 'Purpose' heading's first line);
 * falls back to the first plain prose line. This is what propagates a domain's
 * purpose upward into its parent's Child Docs Index.
 */
export declare function summaryOf(docPath: string): string;
/** True if the doc text contains any alias for the named canonical section. */
export declare function sectionPresent(text: string, name: string): boolean;
