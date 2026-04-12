#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

function readArgs(argv) {
  const output = {};
  for (let index = 0; index < argv.length; index += 1) {
    const current = argv[index];
    if (!current.startsWith('--')) {
      continue;
    }
    const key = current.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith('--')) {
      output[key] = true;
      continue;
    }
    output[key] = next;
    index += 1;
  }
  return output;
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function writeJson(filePath, payload) {
  fs.writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
}

const args = readArgs(process.argv.slice(2));
const repoRoot = path.resolve(String(args.repoRoot ?? '/opt/navly'));
const profileDir = path.resolve(String(args.profileDir ?? '/root/.openclaw-prod'));
const pluginId = 'navly-first-party-host';
const pluginSourceDir = path.join(
  repoRoot,
  'bridges',
  'openclaw-host-bridge',
  'extensions',
  pluginId,
);
const extensionsDir = path.join(profileDir, 'extensions');
const pluginInstallPath = path.join(extensionsDir, pluginId);
const configPath = path.join(profileDir, 'openclaw.json');

ensureDir(extensionsDir);
if (!fs.existsSync(pluginSourceDir)) {
  throw new Error(`plugin source directory does not exist: ${pluginSourceDir}`);
}

try {
  const existingStat = fs.lstatSync(pluginInstallPath);
  if (existingStat.isSymbolicLink() || existingStat.isDirectory()) {
    fs.rmSync(pluginInstallPath, { recursive: true, force: true });
  } else {
    throw new Error(`plugin path exists but is not a directory/symlink: ${pluginInstallPath}`);
  }
} catch {
  // plugin path absent
}

fs.cpSync(pluginSourceDir, pluginInstallPath, {
  recursive: true,
  force: true,
});

const config = fs.existsSync(configPath) ? readJson(configPath) : {};
config.plugins ??= {};
config.plugins.allow = Array.isArray(config.plugins.allow) ? config.plugins.allow : [];
if (!config.plugins.allow.includes(pluginId)) {
  config.plugins.allow.push(pluginId);
}
config.plugins.entries ??= {};
config.plugins.entries[pluginId] = {
  enabled: true,
  config: {
    repoRoot,
    dataPlatformEnvPath: String(args.dataPlatformEnvPath ?? '/etc/navly/data-platform.env'),
    defaultChannel: String(args.defaultChannel ?? 'wecom'),
    channelAccountRef: String(args.channelAccountRef ?? 'openclaw-host-bridge:channel-account:wecom-main'),
    ...(args.defaultScopeRef ? { defaultScopeRef: String(args.defaultScopeRef) } : {}),
    ...(args.defaultOrgId ? { defaultOrgId: String(args.defaultOrgId) } : {}),
    ...(args.defaultAppSecret ? { defaultAppSecret: String(args.defaultAppSecret) } : {}),
  },
};
writeJson(configPath, config);

console.log(JSON.stringify({
  installed: true,
  pluginId,
  pluginSourceDir,
  pluginInstallPath,
  configPath,
}, null, 2));
