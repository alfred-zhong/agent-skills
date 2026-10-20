#!/usr/bin/env node
// Launcher for the bundled Answer me with HTML CLI (scripts/vendor/am-cli.mjs).
// The CLI keeps settings, themes, pages and videos under AM_HOME; upstream
// defaults AM_HOME to ~/.answer-me-with-html. This launcher points it at the
// OS temp directory instead, so run output never lands in the home directory
// or the workspace and the system clears it on its own.
// Set AM_HOME yourself to keep the data directory somewhere persistent.
import { spawn } from 'node:child_process';
import { constants, tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const cli = join(here, 'vendor', 'am-cli.mjs');
const user = String(process.getuid ? process.getuid() : 'user');
const home = join(tmpdir(), 'answer-me-with-html', user);

const env = {
  ...process.env,
  AM_HOME: process.env.AM_HOME || home,
  // This copy is a fork: the CLI's own update hint would point at the upstream
  // package and replace the skill, so update checks stay off.
  AM_NO_UPDATE_CHECK: '1',
};

const child = spawn(process.execPath, [cli, ...process.argv.slice(2)], {
  stdio: 'inherit',
  env,
});

// am serve runs until it is stopped: pass a signal on, so no orphan keeps the port.
for (const signal of ['SIGINT', 'SIGTERM', 'SIGHUP']) {
  process.on(signal, () => child.kill(signal));
}

child.on('error', (error) => {
  console.error(error.message);
  process.exit(1);
});

child.on('exit', (code, signal) => {
  process.exit(signal ? 128 + (constants.signals[signal] ?? 1) : (code ?? 1));
});
