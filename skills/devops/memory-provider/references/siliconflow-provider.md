# SiliconFlow Embedding & VLM Provider Notes

## Embedded from SiliconFlow API (硅基流动)

### Endpoint
```
Base URL: https://api.siliconflow.cn/v1
Auth: Bearer token (Authorization header)
Format: OpenAI-compatible
```

### Verified Embedding Models for OpenViking

| Model | Max Tokens | Dimension | Quality |
|---|---|---|---|
| `BAAI/bge-m3` | 8,192 | 1024 | ⭐ Best multilingual balance |
| `BAAI/bge-large-zh-v1.5` | 512 | 1024 | Chinese-optimized but short limit |
| `BAAI/bge-large-en-v1.5` | 512 | 1024 | English-optimized but short limit |
| `Qwen/Qwen3-Embedding-8B` | 32,768 | 64-4096 (configurable) | Highest quality but more expensive |

**Recommended for OpenViking:** `BAAI/bge-m3` (dimension 1024, good multilingual support, reasonable token limit)

### Verified VLM/Chat Models

| Model | Use Case |
|---|---|
| `Qwen/Qwen3-8B` | Memory extraction (lightweight) |
| `Qwen/Qwen3-14B` | Memory extraction (better quality) |
| `deepseek-ai/DeepSeek-V4-Flash` | Fast, cheap chat |
| `Qwen/Qwen3-32B` | Highest quality extraction |

### Important: Model Name Exactness

The model name must match SiliconFlow's exact ID. Common mistakes:
- ❌ `Qwen/Qwen3-7B` — does NOT exist (use `Qwen/Qwen3-8B`)
- ❌ `Qwen/Qwen3-Embedding` — incomplete (need full version: `Qwen/Qwen3-Embedding-8B`)
- ✅ `BAAI/bge-m3` — correct
- ✅ `Qwen/Qwen3-8B` — correct

### Embedding API Test

```bash
curl -X POST https://api.siliconflow.cn/v1/embeddings \
  -H "Authorization: Bearer $SILICONFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input":"hello","model":"BAAI/bge-m3"}'
```

### Full Model List

To get the current model list:
```
curl -H "Authorization: Bearer $SILICONFLOW_API_KEY" \
  "https://api.siliconflow.cn/v1/models" | jq '.data[].id'
```
