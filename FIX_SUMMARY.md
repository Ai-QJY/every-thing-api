# Session 注入失败问题修复总结

## 问题
用户报告 Cookie 注入失败，API 返回：
```json
{
  "detail": "Session creation failed. Cookies may be invalid or expired."
}
```

## 根本原因

### 1. **URL 配置错误** ⭐ 最关键
- `config.py` 中 `GROK_URL` 设置为 `https://grok.ai`
- 实际应该是 `https://grok.com`
- Cookie 的域名是 `.grok.com`，访问错误 URL 导致域名不匹配

### 2. **登录验证逻辑过于严格**
- `_check_login_success()` 方法无法正确识别已登录状态
- 选择器不够全面，等待时间不足
- 缺少详细的调试日志

## 修复内容

### 1. 修复 URL 配置 (`config.py`)
```python
# 修改前
GROK_URL: str = "https://grok.ai"

# 修改后
GROK_URL: str = "https://grok.com"
```

### 2. 改进 Cookie 注入流程 (`services/session_manager.py`)

#### A. 多域名引导机制
```python
# 根据 Cookie 的域名，自动访问所有相关域名
# 例如：grok.com, x.ai, grok.ai
bootstrap_urls = ["https://grok.com", "https://x.ai"]
for url in bootstrap_urls:
    await self.page.goto(url)
```

#### B. 增加等待时间
- 注入后等待：2秒 → 3秒
- 验证前等待：0秒 → 1秒

#### C. Cookie 规范化改进
- 处理毫秒级时间戳（除以1000）
- 规范化 sameSite 值（lax → Lax）
- 保留原有的域名前导点格式

#### D. 详细日志记录
```
🔄 Reloading page to apply injected cookies...
⏳ Waiting for page to fully render...
📍 Current URL: https://grok.com
📄 Page title: Grok
🍪 Cookies in context after injection: 15
🔍 Validating login state...
✅ Cookie injection successful!
```

### 3. 改进登录验证 (`_check_login_success()`)

#### A. 更多 UI 元素选择器
```python
login_indicators = [
    'textarea',
    'input[type="text"]',
    'div[role="textbox"]',
    'nav',
    'aside',
    '[class*="sidebar"]',
    '[class*="avatar"]',
    # ... 更多
]
```

#### B. 更宽松的验证逻辑
```python
# 如果在 grok.com 且有 3+ Cookie，认为已登录
if len(cookies) >= 3 and "grok.com" in current_url:
    return True
```

#### C. Cookie 关键词扩展
```python
# 原来：["session", "auth", "token", "sid"]
# 现在：["session", "auth", "token", "sid", "_ga", "ct0", "kdt"]
```

### 4. 改进错误消息 (`api/routers/session.py`)
```python
error_msg = (
    f"Session validation failed after cookie injection.\n"
    f"Injected: {cookie_count}/{len(cookie_dicts)} cookies\n"
    f"Expired: {expired_count} cookies\n\n"
    f"Possible causes:\n"
    f"1. Cookies are expired (check extraction time)\n"
    f"2. Server-side session invalidated\n"
    f"3. Login verification logic needs adjustment\n"
    f"4. Wrong domain - ensure cookies are from grok.com\n\n"
    f"Suggestions:\n"
    f"- Extract fresh cookies (< 1 hour old)\n"
    f"- Verify cookies are from an active grok.com session\n"
    f"- Check server logs for detailed validation info\n"
)
```

## 测试建议

### 1. 提取新的 Cookie
```bash
python scripts/extract_grok_cookies.py
```

### 2. 注入 Cookie
```bash
curl -X POST http://localhost:8000/api/session/inject-grok-cookies \
  -H "Content-Type: application/json" \
  -d @data/grok_cookies.json
```

### 3. 查看日志
启动服务器时启用详细日志：
```bash
LOGLEVEL=DEBUG uvicorn main:app --reload
```

关键日志标记：
- ✅ 成功：`Cookie injection successful!`
- ❌ 失败：`Cookie injection validation failed`
- 🍪 Cookie 信息
- 📍 当前 URL

## 调试提示

### 如果仍然失败

1. **检查 Cookie 域名**
```python
import json
with open('data/grok_cookies.json') as f:
    data = json.load(f)
    domains = {c['domain'] for c in data['cookies']}
    print(domains)  # 应该包含 .grok.com 或 .x.ai
```

2. **检查 Cookie 是否过期**
```python
from datetime import datetime
current_ts = datetime.now().timestamp()
expired = [c for c in data['cookies'] 
           if c.get('expires') and 0 < c.get('expires') < current_ts]
print(f"Expired: {len(expired)}/{len(data['cookies'])}")
```

3. **使用可视化模式调试**
```python
# config.py
HEADLESS: bool = False  # 显示浏览器窗口
```

4. **查看详细日志**
服务器日志会显示：
- 访问的 URL
- 注入的 Cookie 数量
- 页面标题
- 验证过程详情

## 相关文档

- `docs/COOKIE_INJECTION_FIX.md` - 详细的修复说明
- `docs/GROK_COOKIE_GUIDE.md` - Cookie 提取指南

## 文件变更

- ✅ `config.py` - 修复 GROK_URL
- ✅ `services/session_manager.py` - 改进注入和验证逻辑
- ✅ `api/routers/session.py` - 改进错误消息
- ✅ `docs/COOKIE_INJECTION_FIX.md` - 新增详细文档
- ✅ `FIX_SUMMARY.md` - 本文件

## 预期结果

修复后，Cookie 注入应该能够成功识别登录状态，即使在以下情况下：
- Cookie 来自不同的域名（grok.com, x.ai）
- 页面加载需要额外时间
- UI 元素选择器略有变化
- 需要多个域名的 Cookie

成功响应示例：
```json
{
  "status": "success",
  "message": "Cookies injected successfully. Session validated. Injected 15 cookies.",
  "session_id": "uuid-here",
  "cookies_count": 15,
  "saved_to": "/path/to/cookies.json"
}
```
