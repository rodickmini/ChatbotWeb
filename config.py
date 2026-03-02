# 模型配置
MODEL_CONFIG = {
    # API配置
    "api_url": "http://localhost:11434/api/chat",
    
    # 模型配置
    "model_name": "Qwen2.5:7B",
    
    # 其他配置
    "stream": False
}

# DeepSeek模型配置
DEEPSEEK_CONFIG = {
    # API配置
    "api_url": "http://222.95.84.214:30003/v1",
    "api_key": "ds-v3.2",
    
    # 模型配置
    "model_name": "Deepseek-V3.2",
    
    # 额外参数
    "extra_body": {
        "chat_template_kwargs": {
            "thinking": False
        }
    }
}

# 默认模型配置
DEFAULT_MODEL = "deepseek"  # 可选值: "local" (本地Qwen) 或 "deepseek" (远程DeepSeek)

# 应用配置
APP_CONFIG = {
    "host": "0.0.0.0",
    "port": 5001,
    "debug": True
}
