#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const args = process.argv.slice(2);
const packageRoot = path.resolve(__dirname, "..", "..");
const wantsLocalRepo = process.env.TRACCIA_USE_LOCAL_REPO === "1";
const configuredSpec = process.env.TRACCIA_UVX_SPEC;
const uvxSpec = configuredSpec && configuredSpec.trim() ? configuredSpec.trim() : "traccia";

function fail(message) {
  process.stderr.write(`${message}\n`);
  process.exit(1);
}

function run(command, commandArgs, options = {}) {
  const result = spawnSync(command, commandArgs, {
    stdio: "inherit",
    env: process.env,
    cwd: options.cwd,
  });

  if (result.error) {
    if (result.error.code === "ENOENT") {
      if (command === "uvx") {
        fail(
          "traccia's npm wrapper needs `uvx` on PATH. install uv first, or use the Python package directly.",
        );
      }

      if (command === "uv") {
        fail("TRACCIA_USE_LOCAL_REPO=1 needs `uv` on PATH.");
      }
    }

    fail(`failed to start ${command}: ${result.error.message}`);
  }

  process.exit(result.status ?? 1);
}

if (wantsLocalRepo) {
  // Local-repo mode is for maintainers testing the wrapper against a checkout.
  if (!fs.existsSync(path.join(packageRoot, "pyproject.toml"))) {
    fail(
      "TRACCIA_USE_LOCAL_REPO=1 only works from a traccia source checkout that contains pyproject.toml.",
    );
  }

  run("uv", ["run", "traccia", ...args], { cwd: packageRoot });
}

run("uvx", ["--from", uvxSpec, "traccia", ...args]);
