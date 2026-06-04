---
name: hermes-custom-provider-model-annotation
title: Hermes Custom Provider Model Annotation
description: How to add model type annotations for custom providers in Hermes Agent, and understand display limitations
category: software-development
tags:
  - hermes
  - custom-providers
  - model-annotation
  - configuration
---

# Hermes Custom Provider Model Annotation

This skill documents how to add model type annotations (text, vision, embedding) for custom providers in Hermes Agent, and explains why these annotations may not display in the model picker interface.

## When to Use

Use this skill when:
1. Configuring a custom provider with multiple model types
2. Wanting to add metadata annotations to models
3. Understanding why annotations don't appear in the model picker
4. Troubleshooting model selection display issues

## Configuration Format

### Basic Provider Configuration

Add model type annotations in the `models` field using dictionary format:

```yaml
custom_providers:
  - name: "your-provider-name"
    base_url: "https://your-api-endpoint.com/v1"
    api_mode: "chat_completions"
    models:
      model-name-1:
        type: "text"
      model-name-2:
        type: "vision"
      model-name-3:
        type: "embedding"

  # 阿里云百炼示例配置
  - name: "aliyun-bailian"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    api_mode: "chat_completions"
    api_key: "${ALIYUN_BAILIAN_API_KEY}"
    models:
      deepseek-v3.2:
        type: "text"
      qwen2.5-vl-72b-instruct:
        type: "vision"
      text-embedding-v3:
        type: "embedding"
      # 其他模型...
```

### Supported Model Types

1. **Text models**: `type: "text"`
2. **Vision models**: `type: "vision"`
3. **Embedding models**: `type: "embedding"`

## Display Limitations

### Current Architecture Constraints

Hermes Agent's model picker has a two-stage architecture that limits annotation display:

1. **Provider selection stage**: Shows "Provider Name (X models)"
2. **Model selection stage**: Shows model name list only

### Data Flow

```
Configuration (dictionary format with annotations)
  ↓ list_authenticated_providers() extracts dictionary KEYS only
  ↓ provider_data["models"] becomes string list (no metadata)
  ↓ Model picker displays string list
```

### Technical Details

The model picker only extracts model names from the dictionary keys and does not preserve or display the metadata values (type annotations).

## Verification Steps

### 1. Check Configuration Format

Ensure the `models` field uses dictionary format with type annotations:

```python
# Example of correct format
models = {
    "model-1": {"type": "text"},
    "model-2": {"type": "vision"},
    "model-3": {"type": "embedding"}
}
```

### 2. Test Model Picker Data

Use the `list_authenticated_providers` function to verify what data the model picker receives:

```python
from hermes_cli.model_switch import list_authenticated_providers

providers = list_authenticated_providers(
    custom_providers=your_config,
    max_models=10
)

# The models field will be a string list, not a dictionary
print(type(provider.get('models')))  # <class 'list'>
print(provider.get('models'))        # ['model-1', 'model-2', 'model-3']
```

## Workarounds and Alternatives

### 1. Model Name Conventions

Use naming conventions to indicate model type within the model name:
- Include `-vl-` or `-vision-` for vision models
- Include `-embedding-` for embedding models
- No special suffix for text models

### 2. Post-Selection Information

After selecting a model, Hermes may display capabilities in the status information:
- Vision models may show "vision" capability
- Text models show standard capabilities

### 3. External Documentation

Maintain a separate documentation file with model classifications for reference.

## Common Issues and Solutions

### Issue: Annotations not showing in model picker
**Solution**: This is expected behavior due to Hermes architecture. Annotations are stored in config but not displayed in the picker UI.

### Issue: Model selection shows empty list
**Solution**: Check that `models` field is a dictionary, not a list. Hermes expects dictionary format for custom providers.

### Issue: Type annotations not recognized
**Solution**: Use consistent English terms: "text", "vision", "embedding".

## Best Practices

1. **Use dictionary format** for models field with type annotations
2. **Test API connections** for each model type
3. **Document model classifications** separately for user reference
4. **Use environment variables** for API keys (not hardcoded in config)

## Future Considerations

If Hermes Agent updates its model picker to support metadata display in the future, the annotations are already in place and will automatically be utilized.

## Related Skills

- `hermes-agent` - General Hermes Agent usage
- `llm-provider-integration` - Integrating LLM providers
- `github-repo-management` - Managing configuration files