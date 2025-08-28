# Claude模型定价配置 (每1M tokens的价格，单位: USD)
# 根据官方价目表更新 - 2025年8月

# 定价模板 - 使用模糊匹配
CLAUDE_PRICING_TEMPLATES = {
    # Claude Opus 4.1 系列 (匹配 claude-opus-4-1-* 或 claude-4-1-*)
    "claude-opus-4-1": {
        "input_tokens": 15.00,
        "output_tokens": 75.00,
        "cache_write_tokens": 18.75,  # 5m cache writes
        "cache_read_tokens": 1.50
    },
    
    # Claude Opus 4 系列 (匹配 claude-opus-4-*)  
    "claude-opus-4": {
        "input_tokens": 15.00,
        "output_tokens": 75.00,
        "cache_write_tokens": 18.75,  # 5m cache writes
        "cache_read_tokens": 1.50
    },
    
    # Claude Sonnet 4 系列 (匹配 claude-sonnet-4-*)
    "claude-sonnet-4": {
        "input_tokens": 3.00,
        "output_tokens": 15.00,
        "cache_write_tokens": 3.75,  # 5m cache writes
        "cache_read_tokens": 0.30
    },
    
    # Claude Sonnet 3.7 系列 (匹配 claude-sonnet-3-7-* 或 claude-3-7-*)
    "claude-sonnet-3-7": {
        "input_tokens": 3.00,
        "output_tokens": 15.00,
        "cache_write_tokens": 3.75,  # 5m cache writes  
        "cache_read_tokens": 0.30
    },
    
    # Claude 3.5 Sonnet 系列 (匹配 claude-3-5-sonnet-*) - deprecated
    "claude-3-5-sonnet": {
        "input_tokens": 3.00,
        "output_tokens": 15.00,
        "cache_write_tokens": 3.75,  # 5m cache writes
        "cache_read_tokens": 0.30
    },
    
    # Claude 3.5 Haiku 系列 (匹配 claude-3-5-haiku-*)
    "claude-3-5-haiku": {
        "input_tokens": 0.80,
        "output_tokens": 4.00,
        "cache_write_tokens": 1.00,  # 5m cache writes
        "cache_read_tokens": 0.08
    },
    
    # Claude 3 Opus 系列 (匹配 claude-3-opus-*) - deprecated
    "claude-3-opus": {
        "input_tokens": 15.00,
        "output_tokens": 75.00,
        "cache_write_tokens": 18.75,  # 5m cache writes
        "cache_read_tokens": 1.50
    },
    
    # Claude 3 Haiku 系列 (匹配 claude-3-haiku-*)
    "claude-3-haiku": {
        "input_tokens": 0.25,
        "output_tokens": 1.25,
        "cache_write_tokens": 0.30,  # 5m cache writes
        "cache_read_tokens": 0.03
    },
    
    # 默认定价 (对于未知模型) - 使用中等价格Sonnet级别
    "default": {
        "input_tokens": 3.00,
        "output_tokens": 15.00,
        "cache_write_tokens": 3.75,
        "cache_read_tokens": 0.30
    }
}

def match_model_pricing(model_name: str) -> dict:
    """
    根据模型名称匹配定价模板
    使用模糊匹配，按照优先级从高到低匹配
    """
    model_lower = model_name.lower()
    
    # 匹配规则，按优先级排序（更具体的模式优先）
    matching_rules = [
        ("claude-opus-4-1", "claude-opus-4-1"),    # 最具体的先匹配
        ("claude-4-1", "claude-opus-4-1"),         # 简化匹配
        ("claude-sonnet-3-7", "claude-sonnet-3-7"),
        ("claude-3-7", "claude-sonnet-3-7"),       # 简化匹配
        ("claude-3-5-haiku", "claude-3-5-haiku"),
        ("claude-3-5-sonnet", "claude-3-5-sonnet"),
        ("claude-sonnet-4", "claude-sonnet-4"),    
        ("claude-opus-4", "claude-opus-4"),
        ("claude-3-opus", "claude-3-opus"),
        ("claude-3-sonnet", "claude-3-sonnet"),
        ("claude-3-haiku", "claude-3-haiku"),
    ]
    
    # 尝试匹配每个规则
    for pattern, pricing_key in matching_rules:
        if pattern in model_lower:
            print(f"模型 {model_name} 匹配到定价模板: {pricing_key}")
            return CLAUDE_PRICING_TEMPLATES[pricing_key]
    
    # 如果没有匹配到任何规则，使用默认定价
    print(f"模型 {model_name} 未匹配到具体定价，使用默认定价")
    return CLAUDE_PRICING_TEMPLATES["default"]

# 保持向后兼容性的精确匹配配置
CLAUDE_MODEL_PRICING = {
    # Claude 3.5 Sonnet
    "claude-3-5-sonnet-20241022": {
        "input_tokens": 3.00,
        "output_tokens": 15.00,
        "cache_write_tokens": 3.75,
        "cache_read_tokens": 0.30
    },
    "claude-3-5-sonnet-20240620": {
        "input_tokens": 3.00,
        "output_tokens": 15.00,
        "cache_write_tokens": 3.75,
        "cache_read_tokens": 0.30
    },
    
    # Claude 3.5 Haiku
    "claude-3-5-haiku-20241022": {
        "input_tokens": 0.8,
        "output_tokens": 4.00,
        "cache_write_tokens": 1,
        "cache_read_tokens": 0.08
    },
    
    # Claude 3 Opus
    "claude-3-opus-20240229": {
        "input_tokens": 15.00,
        "output_tokens": 75.00,
        "cache_write_tokens": 18.75,
        "cache_read_tokens": 1.50
    },
    
    # Claude 3 Sonnet
    "claude-3-sonnet-20240229": {
        "input_tokens": 3.00,
        "output_tokens": 15.00,
        "cache_write_tokens": 3.75,
        "cache_read_tokens": 0.30
    },
    
    # Claude 3 Haiku
    "claude-3-haiku-20240307": {
        "input_tokens": 0.25,
        "output_tokens": 1.25,
        "cache_write_tokens": 0.30,
        "cache_read_tokens": 0.03
    },
    
    # Claude Sonnet 4
    "claude-sonnet-4-20250514": {
        "input_tokens": 3.00,
        "output_tokens": 15.00,
        "cache_write_tokens": 3.75,
        "cache_read_tokens": 0.30
    },
    
    # Claude Opus 4
    "claude-opus-4-20250514": {
        "input_tokens": 15.00,
        "output_tokens": 75.00,
        "cache_write_tokens": 18.75,
        "cache_read_tokens": 1.50
    },
    "claude-opus-4-1-20250805": {
        "input_tokens": 15.00,
        "output_tokens": 75.00,
        "cache_write_tokens": 18.75,
        "cache_read_tokens": 1.50
    },
    
    # 默认定价 (对于未知模型)
    "default": {
        "input_tokens": 3.00,
        "output_tokens": 15.00,
        "cache_write_tokens": 3.75,
        "cache_read_tokens": 0.30
    }
}

def calculate_token_cost(model: str, input_tokens: int = 0, output_tokens: int = 0, 
                        cache_creation_tokens: int = 0, cache_read_tokens: int = 0) -> float:
    """
    计算基于模型的精确token成本
    使用模糊匹配来确定模型价格
    
    Args:
        model: 模型名称 (支持模糊匹配)
        input_tokens: 输入token数量
        output_tokens: 输出token数量  
        cache_creation_tokens: 缓存创建token数量
        cache_read_tokens: 缓存读取token数量
    
    Returns:
        总成本 (USD)
    """
    # 使用模糊匹配获取定价
    pricing = match_model_pricing(model)
    
    # 每个token类型的成本 (转换为每token的价格)
    input_cost = (input_tokens / 1_000_000) * pricing["input_tokens"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_tokens"]
    cache_write_cost = (cache_creation_tokens / 1_000_000) * pricing["cache_write_tokens"]
    cache_read_cost = (cache_read_tokens / 1_000_000) * pricing["cache_read_tokens"]
    
    total_cost = input_cost + output_cost + cache_write_cost + cache_read_cost
    
    return round(total_cost, 8)  # 保留8位小数精度

def get_model_info(model: str) -> dict:
    """获取模型信息"""
    pricing = match_model_pricing(model)
    return {
        "model": model,
        "matched_template": True,  # 标识使用了模糊匹配
        "input_price_per_1m": pricing["input_tokens"],
        "output_price_per_1m": pricing["output_tokens"],
        "cache_write_price_per_1m": pricing["cache_write_tokens"],
        "cache_read_price_per_1m": pricing["cache_read_tokens"]
    }