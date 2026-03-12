# MCP Integrations

This repo now includes a project-scoped MCP configuration in `.mcp.json` for:

- `openbrain-local`: the local Open Brain MCP server from this repo
- `azure-mcp-server`: local Azure operations server started via `npx`
- `microsoft-learn`: remote Microsoft Learn documentation server

## Why this setup

`openbrain-local` is the application surface you are actually building and testing in this repo.

`azure-mcp-server` is useful for Azure operations, discovery, and environment management.

For documentation specifically, `microsoft-learn` is the reliable source of truth. Microsoft documents it as the official remote MCP endpoint for current Learn docs and code samples.

## Prerequisites

1. Install Node.js 20 LTS or later so `npx` is available.
2. Install Azure CLI and run `az login`.
3. Restart Claude Code after adding or changing `.mcp.json`.

## Included configuration

```json
{
  "mcpServers": {
    "openbrain-local": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "-m", "openbrain"]
    },
    "azure-mcp-server": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@azure/mcp@latest", "server", "start"]
    },
    "microsoft-learn": {
      "type": "http",
      "url": "https://learn.microsoft.com/api/mcp"
    }
  }
}
```

## Expected behavior

### Open Brain Local

- Starts the MCP server from this repository over stdio.
- Best for local development, schema validation, and agent workflows against your actual app.
- Requires the project dependencies to be installed with `uv sync`.

### Azure MCP Server

- Uses your local Azure identity.
- Authenticate with `az login` before launching Claude Code.
- Good for subscription/resource-group/resource tooling, including Foundry-related Azure resources.

### Microsoft Learn MCP Server

- No auth required.
- Best source for current Microsoft documentation and official code samples.
- Use this when you need accurate Azure, Foundry, Cosmos, Bicep, SDK, or ARM guidance.

## Recommended usage in this repo

- For app workflows and testing: use `openbrain-local`
- For documentation lookups: use `microsoft-learn`
- For Azure infrastructure tasks: use `azure-mcp-server`

## Optional Claude Code plugins

Microsoft now also publishes Claude Code plugin flows:

- Learn/docs plugin:
  - `/plugin marketplace add microsoftdocs/mcp`
  - `/plugin install microsoft-docs@microsoft-docs-marketplace`
- Azure plugin:
  - `/plugin marketplace add microsoft/skills`
  - `/plugin install azure-skills@skills`

Those plugins are optional. The checked-in `.mcp.json` is the repo-level integration we actually need for this project.

## Why Foundry MCP is not in the default config

- It is useful for Foundry-specific operations, but not necessary for this repo's core delivery loop.
- For this project, Foundry documentation is better handled through `microsoft-learn`.
- Azure resource operations are better handled through `azure-mcp-server` or checked-in deployment scripts.
- We can add Foundry MCP later if you start doing active Foundry-side model, deployment, or agent operations from Claude Code.

## Good prompts

- `Use openbrain-local to store a test task and then read it back.`
- `Use microsoft-learn to find the current Cosmos DB vectorEmbeddingPolicy ARM shape.`
- `Use azure-mcp-server to inspect resource group rg-openbrain-dev and list Cosmos and Container Apps resources.`
- `Use microsoft-learn first, then azure-mcp-server if needed, to verify the correct Azure CLI steps for Container Apps secrets.`

## Sources

- Anthropic Claude Code MCP config docs: https://docs.anthropic.com/en/docs/claude-code/mcp
- Azure MCP Server manual setup for Claude Code and `.mcp.json`: https://github.com/mcp/com.microsoft/azure
- Microsoft Learn MCP overview: https://learn.microsoft.com/en-us/training/support/mcp
- Microsoft Learn MCP getting started: https://learn.microsoft.com/en-us/training/support/mcp-get-started
- Microsoft MCP repo and Azure plugin notes: https://github.com/microsoft/mcp/blob/main/README.md
