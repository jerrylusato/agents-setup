#!/usr/bin/env node

const { spawnSync } = require("node:child_process");
const path = require("node:path");

const packageRoot = path.resolve(__dirname, "..");
const candidates = process.platform === "win32" ? ["py", "python", "python3"] : ["python3", "python"];

function findPython() {
  for (const candidate of candidates) {
    const result = spawnSync(candidate, ["--version"], { encoding: "utf8" });
    if (!result.error && result.status === 0) return candidate;
  }
  return null;
}

const python = findPython();
if (!python) {
  console.error("@jerrylusato/agents requires Python 3.10+ to run.");
  console.error("Install Python, then rerun: npx @jerrylusato/agents --help");
  process.exit(1);
}

const env = {
  ...process.env,
  PYTHONPATH: [packageRoot, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
};

const result = spawnSync(python, ["-m", "agents_cli", ...process.argv.slice(2)], {
  stdio: "inherit",
  env,
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);
