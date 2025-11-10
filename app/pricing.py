# Claude模型定价配置 (每1M tokens的价格，单位: USD)
# 根据官方价目表更新 - 2025年8月
#
# 支持两种定价模式：
# 1. 固定定价：直接使用数字，如 "input_tokens": 3.00
# 2. 分层定价：使用列表，基于累计输入token数量分层，如：
#    "input_tokens": [
#        {"threshold": 200000, "price": 3.00},    # 前200K tokens使用此价格
#        {"threshold": float('inf'), "price": 6.00}  # 超过200K tokens的部分使用此价格
#    ]

# 定价模板 - 使用模糊匹配
CLAUDE_PRICING_TEMPLATES = {
    # Claude Sonnet 4.5 系列 (匹配 claude-sonnet-4-5-*)
    # 支持分层定价：基于请求中的累计输入token数量
    "claude-sonnet-4-5": {
        "input_tokens": [
            {"threshold": 200000, "price": 3.00},    # ≤200K tokens: $3/MTok
            {"threshold": float('inf'), "price": 6.00}  # >200K tokens: $6/MTok
        ],
        "output_tokens": [
            {"threshold": 200000, "price": 15.00},   # ≤200K tokens: $15/MTok
            {"threshold": float('inf'), "price": 22.50}  # >200K tokens: $22.50/MTok
        ],
        "cache_write_tokens": 3.75,  # 缓存写入固定价格
        "cache_read_tokens": 0.30     # 缓存读取固定价格
    },

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
        ("claude-sonnet-4-5", "claude-sonnet-4-5"),  # Claude Sonnet 4.5
        ("claude-4-5", "claude-sonnet-4-5"),         # 简化匹配
        ("claude-opus-4-1", "claude-opus-4-1"),      # 最具体的先匹配
        ("claude-4-1", "claude-opus-4-1"),           # 简化匹配
        ("claude-sonnet-3-7", "claude-sonnet-3-7"),
        ("claude-3-7", "claude-sonnet-3-7"),         # 简化匹配
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

def _calculate_tiered_cost(tokens: int, pricing_config) -> float:
    """
    计算分层定价的成本

    Args:
        tokens: token数量
        pricing_config: 定价配置，可以是：
            - float: 固定价格
            - list: 分层定价配置 [{"threshold": 200000, "price": 3.00}, ...]

    Returns:
        成本 (USD)
    """
    # 如果是固定价格（数字），直接计算
    if isinstance(pricing_config, (int, float)):
        return (tokens / 1_000_000) * pricing_config

    # 如果是分层定价（列表）
    if isinstance(pricing_config, list):
        total_cost = 0.0
        remaining_tokens = tokens
        previous_threshold = 0

        # 按阈值从小到大排序
        tiers = sorted(pricing_config, key=lambda x: x["threshold"])

        for tier in tiers:
            threshold = tier["threshold"]
            price = tier["price"]

            # 计算当前层级可以使用的token数量
            tier_capacity = threshold - previous_threshold
            tokens_in_tier = min(remaining_tokens, tier_capacity)

            if tokens_in_tier > 0:
                # 计算当前层级的成本
                tier_cost = (tokens_in_tier / 1_000_000) * price
                total_cost += tier_cost
                remaining_tokens -= tokens_in_tier

            previous_threshold = threshold

            # 如果没有剩余token，提前退出
            if remaining_tokens <= 0:
                break

        return total_cost

    # 其他情况返回0
    return 0.0


def calculate_token_cost(model: str, input_tokens: int = 0, output_tokens: int = 0,
                        cache_creation_tokens: int = 0, cache_read_tokens: int = 0) -> float:
    """
    计算基于模型的精确token成本
    使用模糊匹配来确定模型价格
    支持固定定价和分层定价两种模式

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

    # 使用分层定价计算函数，自动处理固定价格和分层价格
    input_cost = _calculate_tiered_cost(input_tokens, pricing["input_tokens"])
    output_cost = _calculate_tiered_cost(output_tokens, pricing["output_tokens"])
    cache_write_cost = _calculate_tiered_cost(cache_creation_tokens, pricing["cache_write_tokens"])
    cache_read_cost = _calculate_tiered_cost(cache_read_tokens, pricing["cache_read_tokens"])

    total_cost = input_cost + output_cost + cache_write_cost + cache_read_cost

    return round(total_cost, 8)  # 保留8位小数精度

def get_model_info(model: str) -> dict:
    """获取模型信息，支持固定定��和分层定价显示"""
    pricing = match_model_pricing(model)

    def _format_pricing(pricing_config):
        """格式化定价配置为可读格式"""
        if isinstance(pricing_config, (int, float)):
            return {"type": "fixed", "price": pricing_config}
        elif isinstance(pricing_config, list):
            return {
                "type": "tiered",
                "tiers": [
                    {
                        "threshold": tier["threshold"] if tier["threshold"] != float('inf') else "unlimited",
                        "price": tier["price"]
                    }
                    for tier in sorted(pricing_config, key=lambda x: x["threshold"])
                ]
            }
        return {"type": "unknown", "price": 0}

    return {
        "model": model,
        "matched_template": True,  # 标识使用了模糊匹配
        "input_price_per_1m": _format_pricing(pricing["input_tokens"]),
        "output_price_per_1m": _format_pricing(pricing["output_tokens"]),
        "cache_write_price_per_1m": _format_pricing(pricing["cache_write_tokens"]),
        "cache_read_price_per_1m": _format_pricing(pricing["cache_read_tokens"])
    }