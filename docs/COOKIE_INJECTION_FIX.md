# Cookie 注入修复说明

## 问题描述

在使用提取的 Cookie 进行注入时，遇到了"session 失效"的错误。这个问题是由多个因素导致的。

## 根本原因

### 1. Cookie 注入时机错误 ⚠️
**原问题**：代码先注入 Cookie，然后才导航到目标网站。

```python
# ❌ 错误的顺序
await self.context.add_cookies([...])  # 先注入 cookie
await self.page.goto(config.GROK_URL)  # 后访问页面
```

**为什么会失败**：
- 浏览器在没有访问过域名时，可能无法正确设置该域名的 Cookie
- Cookie 的域名验证会失败，导致 Cookie 被忽略

**修复方案**：
```python
# ✅ 正确的顺序
await self.page.goto(config.GROK_URL)  # 先访问页面，建立域名上下文
await self.context.add_cookies([...])  # 再注入 cookie
await self.page.reload()               # 重新加载以应用 cookie
```

### 2. Cookie 过期未检查
**原问题**：直接注入所有 Cookie，包括已过期的 Cookie。

**修复方案**：
- 在注入前检查 Cookie 的 `expires` 字段
- 过滤掉已过期的 Cookie
- 记录并报告过期的 Cookie 数量

```python
current_timestamp = datetime.now().timestamp()
for cookie in cookies:
    expires = cookie.get("expires")
    if expires and expires > 0 and expires < current_timestamp:
        logging.debug(f"Skipping expired cookie: {cookie['name']}")
        continue
```

### 3. Cookie 域名格式问题
**原问题**：Cookie 域名格式不一致（有的有前导点，有的没有）。

**修复方案**：
- 统一规范化域名格式
- 对于 Grok 相关域名，统一添加前导点（`.grok.com`, `.x.ai`）
- 这样可以确保 Cookie 对所有子域名有效

```python
domain = cookie.get("domain", "").lstrip(".")
if "grok.com" in domain or "x.ai" in domain:
    domain = "." + domain
```

### 4. 登录状态检查不准确
**原问题**：`_check_login_success` 方法使用通用的检查逻辑，无法准确识别 Grok 的登录状态。

**修复方案**：
- 添加多种检查策略
- 检查 URL 中是否包含登录/认证关键词
- 查找 Grok 特定的 UI 元素（聊天框、用户配置等）
- 检查是否存在 Session Cookie
- 综合判断登录状态

## 修复内容

### 1. `services/session_manager.py`

#### 修复 `inject_cookies` 方法
- ✅ 先导航到目标域名，再注入 Cookie
- ✅ 过滤已过期的 Cookie
- ✅ 规范化 Cookie 域名格式
- ✅ 注入后重新加载页面
- ✅ 添加详细的日志记录
- ✅ 改进错误处理

#### 改进 `_check_login_success` 方法
- ✅ 检查 URL 是否在登录页
- ✅ 查找多种登录状态指示器
- ✅ 检查是否存在登录按钮
- ✅ 验证 Session Cookie
- ✅ 综合判断登录状态

### 2. `api/routers/session.py`

#### 改进 `inject_grok_cookies` 端点
- ✅ 添加 Cookie 验证
- ✅ 记录 Cookie 域名信息
- ✅ 提供详细的错误信息
- ✅ 列出可能的失败原因
- ✅ 建议用户下一步操作

### 3. 新增测试脚本

创建 `scripts/test_cookie_injection.py`：
- ✅ 加载保存的 Cookie
- ✅ 检查 Cookie 状态（有效/过期）
- ✅ 测试 Cookie 注入
- ✅ 保持浏览器打开以便检查
- ✅ 提供详细的测试报告

## 使用方法

### 1. 提取 Cookie

```bash
# 使用手动 OAuth 方式提取 Cookie
python scripts/extract_grok_cookies.py
```

### 2. 测试 Cookie 注入

```bash
# 测试保存的 Cookie 是否可以成功注入
python scripts/test_cookie_injection.py
```

### 3. 通过 API 注入

```bash
# 加载保存的 Cookie 并注入
curl -X POST "http://localhost:8000/api/session/inject-grok-cookies" \
  -H "Content-Type: application/json" \
  -d '{
    "cookies": [...],
    "remember_me": true
  }'
```

或者加载已保存的 Cookie：

```bash
curl -X GET "http://localhost:8000/api/session/load-grok-cookies"
```

## 调试技巧

### 1. 查看详细日志

修改日志级别为 DEBUG：

```python
logging.basicConfig(level=logging.DEBUG)
```

### 2. 检查 Cookie 状态

```bash
python scripts/test_cookie_injection.py
```

这个脚本会：
- 显示 Cookie 数量
- 列出所有域名
- 检查过期状态
- 测试注入并保持浏览器打开

### 3. 手动验证

1. 在浏览器开发者工具中查看 Cookie
2. 确认 Cookie 的域名和过期时间
3. 检查是否有 `auth_token` 或 `session_id` 等关键 Cookie

## 常见问题

### Q1: Cookie 注入成功但仍然显示未登录

**可能原因**：
1. Cookie 已过期
2. Session 在服务器端已失效
3. 需要额外的认证步骤（如 2FA）
4. Cookie 的域名不匹配

**解决方法**：
1. 重新提取新的 Cookie
2. 确认在浏览器中可以正常访问
3. 检查是否需要完成额外的认证步骤

### Q2: 部分 Cookie 注入失败

**可能原因**：
1. Cookie 格式不正确
2. 域名不匹配
3. 安全属性限制（如 `secure`, `httpOnly`）

**解决方法**：
1. 查看日志中的警告信息
2. 确认失败的是哪些 Cookie
3. 检查这些 Cookie 的属性

### Q3: 注入后页面立即跳转到登录页

**可能原因**：
1. 关键的认证 Cookie 缺失或无效
2. Session 已在服务器端失效
3. IP 地址或 User-Agent 验证失败

**解决方法**：
1. 提取时和注入时使用相同的 User-Agent
2. 确保提取的 Cookie 完整
3. 尝试在同一网络环境下操作

## 最佳实践

### 1. Cookie 提取
- ✅ 使用持久化浏览器配置（避免无痕模式）
- ✅ 完整完成登录流程
- ✅ 等待页面完全加载
- ✅ 立即保存提取的 Cookie

### 2. Cookie 注入
- ✅ 使用新鲜的 Cookie（建议 < 1 小时）
- ✅ 使用相同的 User-Agent
- ✅ 确保 Cookie 未过期
- ✅ 检查注入后的验证结果

### 3. 错误处理
- ✅ 记录详细的日志
- ✅ 保留浏览器窗口以便调试
- ✅ 检查返回的错误信息
- ✅ 必要时重新提取 Cookie

## 技术细节

### Cookie 属性说明

| 属性 | 说明 | 重要性 |
|------|------|--------|
| `name` | Cookie 名称 | ⭐⭐⭐ |
| `value` | Cookie 值 | ⭐⭐⭐ |
| `domain` | 作用域名 | ⭐⭐⭐ |
| `path` | 作用路径 | ⭐⭐ |
| `expires` | 过期时间 | ⭐⭐⭐ |
| `httpOnly` | 禁止 JS 访问 | ⭐ |
| `secure` | 仅 HTTPS | ⭐⭐ |
| `sameSite` | 跨站策略 | ⭐⭐ |

### 注入流程

```
1. 初始化浏览器上下文
   ↓
2. 导航到目标域名（建立域名上下文）
   ↓
3. 过滤已过期的 Cookie
   ↓
4. 规范化 Cookie 格式
   ↓
5. 逐个注入 Cookie
   ↓
6. 重新加载页面（应用 Cookie）
   ↓
7. 验证登录状态
   ↓
8. 保存 Session 信息
```

## 相关文件

- `services/session_manager.py` - Session 管理和 Cookie 注入
- `services/cookie_extractor.py` - Cookie 提取逻辑
- `api/routers/session.py` - API 端点
- `scripts/test_cookie_injection.py` - 测试脚本
- `config.py` - 配置文件

## 更新历史

- **2024-01-XX**: 初始版本，修复 Cookie 注入 Session 失效问题
  - 修复注入时机
  - 添加过期检查
  - 改进登录验证
  - 增强错误处理
