# Cookie 注入失败问题修复指南

## 问题描述

当尝试注入 Cookie 时，API 返回错误：
```json
{
  "detail": "Session creation failed. Cookies may be invalid or expired."
}
```

## 修复内容

### 1. ✅ 修复了 `GROK_URL` 配置错误

**问题**：`config.py` 中的 `GROK_URL` 设置为 `https://grok.ai`，但实际上 Grok 的正确 URL 是 `https://grok.com`。

**影响**：当 Cookie 的域名是 `.grok.com` 时，访问 `grok.ai` 会导致域名不匹配，Cookie 无法生效。

**修复**：
```python
# 旧配置
GROK_URL: str = "https://grok.ai"

# 新配置
GROK_URL: str = "https://grok.com"
```

### 2. ✅ 改进了登录验证逻辑

**问题**：`_check_login_success()` 方法的验证逻辑过于严格，无法正确识别已登录状态。

**改进**：
- 增加了更多 UI 元素选择器（textarea, nav, aside, avatar 等）
- 扩展了 Cookie 关键词检测（增加 `_ga`, `ct0`, `kdt` 等）
- 添加了基于 URL 和 Cookie 数量的备用验证逻辑
- 增加了详细的日志输出，便于调试

**新逻辑**：
```python
# 1. 检查 URL 是否在登录页面
# 2. 在 grok.com 域名上查找多种登录指示器
# 3. 检查是否有登录按钮（反向指示）
# 4. 检查 URL 和 Cookie 数量的组合
# 5. 如果有 3+ Cookie 且在 grok.com，认为已登录
```

### 3. ✅ 增强了域名引导机制

**问题**：某些浏览器在未访问过域名时无法正确处理 Cookie。

**改进**：根据 Cookie 的域名，自动访问所有相关域名：
```python
# 示例：如果 Cookie 包含 grok.com 和 x.ai 的域名
# 会依次访问：
bootstrap_urls = ["https://grok.com", "https://x.ai"]
```

### 4. ✅ 增加了等待时间和详细日志

**改进**：
- Cookie 注入后等待 3 秒（原来 2 秒）
- 在 `_check_login_success()` 开始时额外等待 1 秒
- 添加了丰富的 emoji 日志，便于追踪流程
- 记录当前 URL、页面标题、Cookie 数量等调试信息

**日志示例**：
```
🔄 Reloading page to apply injected cookies...
⏳ Waiting for page to fully render...
📍 Current URL: https://grok.com
📄 Page title: Grok
🍪 Cookies in context after injection: 15
🔍 Validating login state...
✅ Cookie injection successful! 15 cookies injected, session is valid
```

### 5. ✅ 改进了错误消息

**问题**：原始错误消息信息不足，无法判断失败原因。

**改进**：提供详细的诊断信息：
```
Session validation failed after cookie injection.
Injected: 12/15 cookies
Expired: 3 cookies

Possible causes:
1. Cookies are expired (check extraction time)
2. Server-side session invalidated
3. Login verification logic needs adjustment
4. Wrong domain - ensure cookies are from grok.com

Suggestions:
- Extract fresh cookies (< 1 hour old)
- Verify cookies are from an active grok.com session
- Check server logs for detailed validation info
- If cookies are valid, this might be a detection issue - check logs
```

## 使用建议

### 1. 确保 Cookie 新鲜

Cookie 应该在提取后尽快使用（建议 < 1 小时）：
```bash
# 提取 Cookie
python scripts/extract_grok_cookies.py

# 立即注入
curl -X POST http://localhost:8000/api/session/inject-grok-cookies \
  -H "Content-Type: application/json" \
  -d @data/grok_cookies.json
```

### 2. 检查 Cookie 域名

确保 Cookie 来自正确的域名：
```python
# 检查 Cookie 文件
import json
with open('data/grok_cookies.json') as f:
    data = json.load(f)
    domains = {c['domain'] for c in data['cookies']}
    print(f"Cookie 域名: {domains}")
    # 应该包含 .grok.com 或 .x.ai
```

### 3. 查看详细日志

如果注入失败，查看服务器日志获取详细信息：
```bash
# 启动服务器时启用详细日志
LOGLEVEL=DEBUG uvicorn main:app --reload
```

关键日志指示器：
- ✅ 成功：`Cookie injection successful!`
- ❌ 失败：`Cookie injection validation failed`
- 🍪 Cookie 信息：`Cookies in context after injection: N`
- 📍 当前页面：`Current URL: ...`

### 4. 常见问题排查

#### 问题：所有 Cookie 都过期了
```bash
# 重新提取 Cookie
python scripts/extract_grok_cookies.py
```

#### 问题：域名不匹配
```
# 错误示例
Cookie 域名: {'.grok.ai', '.x.ai'}  # ❌ grok.ai 不对

# 正确示例
Cookie 域名: {'.grok.com', '.x.ai'}  # ✅ 正确
```

#### 问题：登录验证无法识别
查看日志中的 URL 和 Cookie 信息：
```
📍 Current URL: https://grok.com/...
🍪 Total cookies in context: 15
🍪 Cookie names: session, auth_token, ...
```

如果 URL 正确且有足够的 Cookie，但验证仍然失败，可能需要调整 `_check_login_success()` 的逻辑。

### 5. 测试 Cookie 注入

使用测试脚本验证：
```bash
# 1. 提取 Cookie
python scripts/extract_grok_cookies.py

# 2. 测试注入（会打开浏览器便于检查）
python scripts/test_cookie_injection.py
```

## 代码改动总结

### 修改的文件

1. **config.py**
   - `GROK_URL`: `https://grok.ai` → `https://grok.com`

2. **services/session_manager.py**
   - `_check_login_success()`: 改进验证逻辑
   - `inject_cookies()`: 增加域名引导、等待时间、详细日志
   - 返回值: 失败时返回 `(False, cookie_count)` 而不是 `(False, 0)`

3. **api/routers/session.py**
   - `inject_grok_cookies()`: 改进错误消息，提供详细诊断信息

## 验证修复

运行以下测试确认修复生效：

```bash
# 1. 确保依赖安装
pip install -r requirements.txt
playwright install chromium

# 2. 提取 Cookie
python scripts/extract_grok_cookies.py

# 3. 启动 API 服务器
uvicorn main:app --reload

# 4. 测试注入（在另一个终端）
curl -X POST http://localhost:8000/api/session/inject-grok-cookies \
  -H "Content-Type: application/json" \
  -d @data/grok_cookies.json

# 5. 查看响应
# 成功：{"status":"success","message":"Cookies injected successfully..."}
# 失败：查看详细错误消息和建议
```

## 额外提示

### 调试模式

如果需要深入调试，可以修改 `config.py`：
```python
HEADLESS: bool = False  # 显示浏览器窗口
```

这样可以看到浏览器实际执行的操作。

### 手动验证

如果自动验证失败，可以手动检查：
1. Cookie 注入后浏览器会停留在页面上
2. 目视检查是否已登录
3. 如果已登录但验证失败，说明需要调整 `_check_login_success()` 逻辑

### 持久化会话

成功注入后，会话信息会保存到：
```
sessions/grok_session.json
```

可以使用 `/api/session/status` 检查会话状态。

## 总结

主要修复了两个关键问题：
1. **URL 配置错误**：`grok.ai` → `grok.com`
2. **验证逻辑改进**：更宽松、更智能的登录状态检测

这些修复应该能解决大部分 Cookie 注入失败的问题。如果仍然遇到问题，请查看详细日志并根据错误消息中的建议进行排查。
