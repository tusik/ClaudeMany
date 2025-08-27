# ClaudeMany

A high-performance proxy server for Anthropic Claude API with comprehensive API key management, rate limiting, and usage analytics.

## ✨ Features

- 🔐 **API Key Management** - Create, manage, and monitor multiple API keys
- ⚡ **Smart Rate Limiting** - Per-key request rate control with real-time monitoring
- 🖥️ **Web Dashboard** - Modern web interface for easy management
- 🔄 **Multi-Backend Support** - Dynamic switching between different Claude API endpoints
- 📊 **Usage Analytics** - Detailed statistics, cost tracking, and trend visualization
- 🚀 **High Performance** - Optimized proxy with connection pooling
- 🛡️ **Security** - JWT authentication and secure API key hashing

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/yourusername/ClaudeMany
cd ClaudeMany
pip install -r requirements.txt
```

### Configuration

Create `.env` file:

```env
# Anthropic API Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_BASE_URL=https://api.anthropic.com

# Database
DATABASE_URL=sqlite:///./claude_proxy.db

# Security
SECRET_KEY=your_secret_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Admin Account
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_admin_password_here

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Default Limits
DEFAULT_RATE_LIMIT=1000
DEFAULT_QUOTA_LIMIT=100000
```

### Launch

```bash
python main.py
```

### Access Dashboard

Open http://localhost:8000 and login with your admin credentials to start managing API keys.

## 📱 Web Dashboard

### API Key Management
- Create and configure API keys with custom rate limits
- Real-time usage monitoring and statistics
- In-table editing for quick configuration updates

### Backend Management  
- Configure multiple Claude API backends
- One-click backend switching
- Health monitoring and failover

### Analytics Dashboard
- Daily usage trends and cost analysis
- Per-key performance metrics
- Visual charts and reporting

## 🔧 API Usage

### Proxy Requests

All requests to `/v1/*` are proxied to Claude API:

```python
import requests

response = requests.post("http://localhost:8000/v1/messages",
    headers={
        "x-api-key": "your_proxy_api_key",
        "Content-Type": "application/json"
    },
    json={
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": "Hello!"}]
    })
```

### Rate Limiting

When rate limits are exceeded, the server returns `429 Too Many Requests` with helpful headers:

- `X-RateLimit-Limit` - Rate limit value
- `X-RateLimit-Remaining` - Remaining requests  
- `X-RateLimit-Reset` - Reset time
- `Retry-After` - Seconds to wait

### Admin API

```python
# Create API key
requests.post("http://localhost:8000/admin/api-keys",
    headers={"Authorization": f"Bearer {admin_token}"},
    json={"name": "My App", "rate_limit": 1000, "quota_limit": 50000})

# Update rate limits
requests.put("http://localhost:8000/admin/api-keys/{key_id}",
    headers={"Authorization": f"Bearer {admin_token}"},
    json={"rate_limit": 2000})
```

## 🐳 Docker Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "main.py"]
```

```bash
docker build -t claudemany .
docker run -p 8000:8000 --env-file .env claudemany
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.