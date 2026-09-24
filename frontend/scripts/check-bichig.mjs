/**
 * Regression checks for Cyrillic → Mongol bichig conversion.
 * Run: node --input-type=module scripts/check-bichig.mjs
 * (expects /tmp/bichig.bundle.mjs from esbuild, or builds it)
 */
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const bundle = "/tmp/bichig.bundle.mjs";
const src = join(root, "src/lib/bichig.ts");

const build = spawnSync(
  "npx",
  ["esbuild", src, "--bundle", "--platform=node", "--format=esm", `--outfile=${bundle}`],
  { cwd: root, encoding: "utf8" },
);
if (build.status !== 0) {
  console.error(build.stderr || build.stdout);
  process.exit(1);
}

const { cyrillicToBichig } = await import(bundle);

const HELTES = "ᢈᠡᠯᠲᠡᠰ";
const NNBSP = "\u202F";

/** @type {Array<[string, (out: string) => void]>} */
const cases = [
  [
    "хэлтэс",
    (out) => {
      assert(out === HELTES, `хэлтэс → ${JSON.stringify(out)}`);
      assert(!out.includes("!"), "no ASCII !");
      assert(!out.includes(NNBSP), "solid stem has no NNBSP mid-word");
    },
  ],
  [
    "хэлтэсийн",
    (out) => {
      assert(out.startsWith(HELTES), `хэлтэсийн starts with stem: ${JSON.stringify(out)}`);
      assert(!out.includes("ᠡᠴᠡ"), "not false ablative эс");
    },
  ],
  [
    "хэлтэсэд",
    (out) => {
      assert(out.startsWith(HELTES), `хэлтэсэд starts with stem: ${JSON.stringify(out)}`);
      assert(!out.includes("ᠡᠴᠡ"), "not false ablative эс");
    },
  ],
  [
    "хэлтэстэй",
    (out) => {
      assert(out.startsWith(HELTES), `хэлтэстэй starts with stem: ${JSON.stringify(out)}`);
    },
  ],
  [
    "хэлтэсээс",
    (out) => {
      assert(out.startsWith(HELTES), `хэлтэсээс starts with stem: ${JSON.stringify(out)}`);
    },
  ],
  [
    "монгол",
    (out) => {
      assert(out === "ᠮᠣᠩᠭᠣᠯ", `монгол override: ${JSON.stringify(out)}`);
    },
  ],
  [
    "төгөлдөр",
    (out) => {
      assert(!out.includes(NNBSP) || out.length > 4, `төгөлдөр ok: ${JSON.stringify(out)}`);
      assert(out.includes("ᠲ"), "has ᠲ");
    },
  ],
];

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

let failed = 0;
for (const [input, check] of cases) {
  try {
    const out = cyrillicToBichig(input);
    check(out);
    console.log("ok", input, "→", out);
  } catch (err) {
    failed += 1;
    console.error("FAIL", input, err instanceof Error ? err.message : err);
  }
}

if (!existsSync(bundle)) process.exit(1);
process.exit(failed ? 1 : 0);
