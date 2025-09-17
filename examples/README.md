# Usage Examples

## Python (asyncio + `mcp` library)

```python
import asyncio
from mcp.client.stdio import StdioClient

async def main() -> None:
    # Launch the server (replace with the path to your installed package or container entrypoint)
    async with StdioClient.start(["python", "-m", "kali_mcp_server.server"]) as client:
        categories = await client.call_tool("list_categories")
        print(categories.text)

        search = await client.call_tool("search_tools", {"query": "wireless"})
        print(search.text)

        result = await client.call_tool(
            "run_kali_tool",
            {"tool_name": "nmap", "arguments": "-sV 127.0.0.1", "timeout": 90},
        )
        print(result.text)

if __name__ == "__main__":
    asyncio.run(main())
```

> Depending on the SDK version you may need to adjust the import path (the snippet
> assumes `mcp` ≥ 1.2.0 which ships `mcp.client.stdio.StdioClient`).

> Requires `pip install mcp` (version 1.2.0 or later) and access to the Kali MCP server binary.

## CLI

```bash
# 1. Build the image (or pull ghcr.io/h47r15/kali-mcp-server:latest)
 docker build -t ghcr.io/h47r15/kali-mcp-server:latest .

# 2. Start an MCP inspector session
 npx @modelcontextprotocol/inspector docker run -i --rm \
   -v /var/run/docker.sock:/var/run/docker.sock \
   -v "$HOME/.docker/mcp:/mcp" \
   ghcr.io/h47r15/kali-mcp-server:latest \
   --catalog=/mcp/catalogs/custom.yaml \
   --registry=/mcp/registry.yaml \
   --transport=stdio

# 3. From the inspector, invoke tools such as:
#    list_categories, list_tools {"category": "Information Gathering"},
#    run_kali_tool {"tool_name": "nmap", "arguments": "-sV 127.0.0.1"}

## Direct container run (no inspector)

```bash
docker run --rm -it \
  -v "$PWD/data:/app/data" \
  -v "$PWD/config:/app/config" \
  -e KALI_TOOL_DATA=/app/data/kali_tools.json \
  -e KALI_POLICY_FILE=/app/config/policy.yaml \
  ghcr.io/h47r15/kali-mcp-server:latest \
  kali-mcp-server
```

Omit the volume mounts if you want to rely on the packaged dataset/policy.
```

See the README for additional setup steps, dataset refresh instructions, and policy configuration.
