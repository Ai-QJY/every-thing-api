# Cookie 提取和注入 - 快速指南

## 🚀 快速开始

### 1️⃣ 提取 Cookie

```bash
python scripts/extract_grok_cookies.py
```

浏览器会打开，完成 Google 登录后 Cookie 会自动保存到 `data/grok_cookies.json`。

### 2️⃣ 检查 Cookie 状态

```bash
python scripts/check_cookies.py
```

这会显示：
- ✅ 有效 Cookie 数量
- ❌ 过期 Cookie 数量
- 🕐 Session Cookie 数量
- 🔑 重要的认证 Cookie
- ⏰ Cookie 年龄

### 3️⃣ 测试注入

```bash
python scripts/test_cookie_injection.py
```

这会：
- 加载保存的 Cookie
- 执行注入
- 验证登录状态
- 保持浏览器打开 5 分钟以便检查

### 4️⃣ 使用 API 注入

```python
import requests

# 方式1：从文件加载并注入
response = requests.get("http://localhost:8000/api/session/load-grok-cookies")
cookies = response.json()["cookies"]

response = requests.post(
    "http://localhost:8000/api/session/inject-grok-cookies",
    json={"cookies": cookies, "remember_me": True}
)

print(response.json())
```

## 📋 工作流程

```
提取 Cookie
    ↓
检查状态（可选）
    ↓
测试注入（推荐）
    ↓
在应用中使用
```

## 🛠️ 实用脚本

| 脚本 | 用途 |
|------|------|
| `extract_grok_cookies.py` | 提取 Cookie（手动 OAuth） |
| `check_cookies.py` | 快速检查 Cookie 状态 |
| `test_cookie_injection.py` | 测试 Cookie 注入功能 |

## 💡 最佳实践

### ✅ DO

- ✅ 提取后立即使用（< 1 小时最佳）
- ✅ 定期检查 Cookie 状态
- ✅ 使用测试脚本验证注入
- ✅ 查看详细日志了解问题
- ✅ 使用相同的 User-Agent

### ❌ DON'T

- ❌ 使用过期的 Cookie
- ❌ 跳过 Cookie 状态检查
- ❌ 忽略日志中的警告
- ❌ 在不同环境使用同一 Cookie
- ❌ 频繁重复提取（会触发安全机制）

## 🔍 故障排查

### Cookie 注入失败？

```bash
# 1. 检查 Cookie 状态
python scripts/check_cookies.py

# 2. 如果过期，重新提取
python scripts/extract_grok_cookies.py

# 3. 测试注入
python scripts/test_cookie_injection.py
```

### 验证失败？

1. 📊 查看日志输出
2. 🔍 检查浏览器中的 Cookie
3. 🔄 尝试重新提取
4. 📚 参考详细文档

## 📚 详细文档

- `COOKIE_INJECTION_FIX_SUMMARY.md` - 修复总结
- `docs/COOKIE_INJECTION_FIX.md` - 技术细节
- `docs/GROK_COOKIE_GUIDE.md` - 完整指南

## 🎯 常见场景

### 场景 1：首次使用

```bash
# 提取
python scripts/extract_grok_cookies.py

# 检查
python scripts/check_cookies.py

# 测试
python scripts/test_cookie_injection.py
```

### 场景 2：Cookie 过期

```bash
# 检查状态
python scripts/check_cookies.py

# 如果过期，重新提取
python scripts/extract_grok_cookies.py
```

### 场景 3：注入失败调试

```bash
# 测试注入（会保持浏览器打开）
python scripts/test_cookie_injection.py

# 在浏览器中检查：
# - Cookie 是否正确设置
# - 页面是否显示登录状态
# - 控制台是否有错误
```

## ⚡ 快捷命令

```bash
# 一键检查和测试
python scripts/check_cookies.py && python scripts/test_cookie_injection.py

# 提取并测试
python scripts/extract_grok_cookies.py && python scripts/test_cookie_injection.py
```

## 🐛 调试技巧

### 启用详细日志

在脚本开头添加：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 检查 Cookie 详情

```python
from services.cookie_extractor import load_cookies_from_file
import json

cookies = load_cookies_from_file()
print(json.dumps(cookies, indent=2))
```

### 手动测试单个 Cookie

```python
import asyncio
from services.session_manager import SessionManager

async def test():
    sm = SessionManager()
    success, count = await sm.inject_cookies([{
        "name": "your_cookie_name",
        "value": "your_cookie_value",
        "domain": ".grok.com",
        "path": "/"
    }])
    print(f"Success: {success}, Count: {count}")

asyncio.run(test())
```

## 📞 需要帮助？

1. 🔍 查看脚本输出的详细信息
2. 📊 检查日志文件
3. 📚 阅读详细文档
4. 🧪 使用测试脚本调试

---

**提示**：大多数问题都可以通过重新提取新的 Cookie 解决！
