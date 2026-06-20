import { Config } from "./config.js";
export interface Args {
    scaffold?: boolean;
    strict?: boolean;
    path?: string;
}
export declare function cmdInit(root: string, cfg: Config, args: Args): number;
export declare function syncAll(root: string, cfg: Config, write: boolean): number;
export declare function cmdSync(root: string, cfg: Config): number;
export declare function cmdCheck(root: string, cfg: Config, args: Args): number;
export declare function cmdContext(root: string, cfg: Config, args: Args): number;
