// Sinh public/sw-version.js trước mỗi build để service worker tự đổi cache.
// Chạy tự động qua npm script "prebuild".
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const pkg = JSON.parse(readFileSync(join(root, "package.json"), "utf-8"));
const stamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, "");
const version = `${pkg.version}+${stamp}`;
writeFileSync(
  join(root, "public", "sw-version.js"),
  `// Tự sinh bởi scripts/gen-sw-version.mjs — không sửa tay.\nself.AURUM_SW_VERSION = ${JSON.stringify(version)};\n`,
);
console.log(`sw-version: ${version}`);
