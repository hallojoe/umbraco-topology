import { readFileSync } from 'node:fs';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const config = JSON.parse(readFileSync(new URL('../.mcp.json', import.meta.url))).mcpServers['__PROJECT_SLUG__'];
const transport = new StdioClientTransport({ command: config.command, args: config.args, env: { ...process.env, ...config.env } });
const client = new Client({ name: '__PROJECT_SLUG__-check', version: '1.0.0' });
try {
  await client.connect(transport);
  const tools = await client.listTools();
  const result = await client.callTool({
    name: 'get-document-by-id',
    arguments: { id: '32a9a9ac-7f72-4d8f-ad5b-ee9f771b5e1f' },
  });
  if (result.isError) throw new Error('Home document read failed');
  console.log(`MCP initialized; ${tools.tools.length} tools; published Home read succeeded.`);
} finally {
  await client.close();
}
