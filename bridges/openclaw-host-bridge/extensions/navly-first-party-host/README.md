# Navly First-Party Host Plugin

This OpenClaw plugin publishes Navly's first-party capability-oriented host surface:

- 10 runtime tools from `tool-publication/first-party-tool-publication.manifest.json`
- 7 bundled skills from `skills/`

The plugin is deployment-owned glue. It does not invent business truth. It loads:

- the committed Navly host publication manifest
- the existing `runFirstPartyLiveHostTool(...)` bridge/runtime handoff
- live data-platform defaults from a configured env file such as `/etc/navly/data-platform.env`

Server install is handled by:

- `bridges/openclaw-host-bridge/scripts/install-navly-first-party-host-plugin.mjs`
