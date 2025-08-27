# Claude模型定价配置 (每1M tokens的价格，单位: USD)

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
        "input_tokens": 1.00,
        "output_tokens": 5.00,
        "cache_write_tokens": 1.25,
        "cache_read_tokens": 0.10
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
        "input_tokens": 5.00,
        "output_tokens": 25.00,
        "cache_write_tokens": 6.25,
        "cache_read_tokens": 0.50
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
    
    Args:
        model: 模型名称
        input_tokens: 输入token数量
        output_tokens: 输出token数量  
        cache_creation_tokens: 缓存创建token数量
        cache_read_tokens: 缓存读取token数量
    
    Returns:
        总成本 (USD)
    """
    # 获取模型定价，如果模型不存在则使用默认定价
    pricing = CLAUDE_MODEL_PRICING.get(model, CLAUDE_MODEL_PRICING["default"])
    
    # 每个token类型的成本 (转换为每token的价格)
    input_cost = (input_tokens / 1_000_000) * pricing["input_tokens"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_tokens"]
    cache_write_cost = (cache_creation_tokens / 1_000_000) * pricing["cache_write_tokens"]
    cache_read_cost = (cache_read_tokens / 1_000_000) * pricing["cache_read_tokens"]
    
    total_cost = input_cost + output_cost + cache_write_cost + cache_read_cost
    
    return round(total_cost, 8)  # 保留8位小数精度

def get_model_info(model: str) -> dict:
    """获取模型信息"""
    pricing = CLAUDE_MODEL_PRICING.get(model, CLAUDE_MODEL_PRICING["default"])
    return {
        "model": model,
        "input_price_per_1m": pricing["input_tokens"],
        "output_price_per_1m": pricing["output_tokens"],
        "cache_write_price_per_1m": pricing["cache_write_tokens"],
        "cache_read_price_per_1m": pricing["cache_read_tokens"]
    }