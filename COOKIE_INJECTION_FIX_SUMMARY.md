# Cookie 注入 Session 失效问题 - 修复总结

## 🔧 修复的问题

获取到的 Cookie 去注入的时候报错，提示 session 失效。

## ✅ 主要修复

### 1. 修复 Cookie 注入时机（核心问题）

**问题**：代码先注入 Cookie，后访问页面，导致 Cookie 无法正确设置。

**修复**：
```python
# 修改前（错误）❌
await self.context.add_cookies([cookie])  # 先注入
await self.page.goto(url)                  # 后访问

# 修改后（正确）✅
await self.page.goto(url)                  # 先访问，建立域名上下文
await self.context.add_cookies([cookie])  # 再注入
await self.page.reload()                   # 重新加载应用 Cookie
```

### 2. 添加 Cookie 过期检查

**问题**：没有过滤已过期的 Cookie，导致无效 Cookie 被注入。

**修复**：
- 检查 `expires` 时间戳
- 过滤掉已过期的 Cookie
- 记录有效和过期的 Cookie 数量

### 3. 规范化 Cookie 域名格式

**问题**：Cookie 域名格式不统一（`.grok.com` vs `grok.com`）。

**修复**：
- 统一添加前导点：`.grok.com`, `.x.ai`
- 确保 Cookie 对所有子域名有效

### 4. 改进登录状态验证

**问题**：`_check_login_success` 方法检查逻辑不准确。

**修复**：
- 检查 URL 是否在登录页
- 查找 Grok 特定的 UI 元素
- 检查 Session Cookie
- 综合判断登录状态

### 5. 增强日志和错误处理

**问题**：错误信息不够详细，难以调试。

**修复**：
- 详细记录每个步骤
- 显示 Cookie 域名、过期状态
- 提供失败原因和解决建议

## 📝 修改的文件

1. **`services/session_manager.py`**
   - `inject_cookies()` - 修复注入逻辑
   - `_check_login_success()` - 改进登录验证

2. **`api/routers/session.py`**
   - `inject_grok_cookies()` - 增强错误处理和日志

3. **新增文件**
   - `scripts/test_cookie_injection.py` - Cookie 注入测试工具
   - `docs/COOKIE_INJECTION_FIX.md` - 详细文档

## 🧪 测试方法

### 方法 1：使用测试脚本

```bash
# 1. 提取 Cookie
python scripts/extract_grok_cookies.py

# 2. 测试注入
python scripts/test_cookie_injection.py
```

测试脚本会：
- ✅ 加载保存的 Cookie
- ✅ 显示 Cookie 状态（有效/过期）
- ✅ 执行注入并验证
- ✅ 保持浏览器打开 5 分钟以便检查

### 方法 2：使用 API

```bash
# 1. 提取 Cookie（手动 OAuth）
curl -X POST "http://localhost:8000/api/session/extract-grok-cookies-manual" \
  -H "Content-Type: application/json" \
  -d '{"timeout": 600}'

# 2. 注入 Cookie
curl -X POST "http://localhost:8000/api/session/inject-grok-cookies" \
  -H "Content-Type: application/json" \
  -d '{"cookies": [...], "remember_me": true}'
```

## 🎯 使用建议

### Cookie 提取
1. ✅ 使用持久化浏览器配置（非无痕模式）
2. ✅ 确保完整完成登录流程
3. ✅ 等待页面完全加载后再提取
4. ✅ 立即保存提取的 Cookie

### Cookie 注入
1. ✅ 使用新鲜的 Cookie（建议 < 1 小时）
2. ✅ 提取和注入使用相同的 User-Agent
3. ✅ 确保 Cookie 未过期
4. ✅ 检查注入后的日志和浏览器状态

### 调试技巧
1. 📊 查看详细日志（设置 `logging.DEBUG`）
2. 🔍 使用测试脚本保持浏览器打开以检查状态
3. 🍪 在浏览器开发者工具中验证 Cookie
4. 🔄 如果失败，重新提取新的 Cookie

## ⚠️ 常见问题

### Q: Cookie 注入成功但仍显示未登录？

**可能原因**：
- Cookie 已过期
- Session 在服务器端已失效
- 需要额外认证（如 2FA）

**解决方法**：
1. 重新提取新的 Cookie
2. 确认在浏览器中可以正常访问
3. 检查日志中的详细信息

### Q: 部分 Cookie 注入失败？

**可能原因**：
- Cookie 格式不正确
- 域名不匹配
- 安全属性限制

**解决方法**：
1. 查看日志中的警告信息
2. 确认失败的 Cookie 名称
3. 检查这些 Cookie 的属性

## 📚 相关文档

详细技术文档请查看：
- `docs/COOKIE_INJECTION_FIX.md` - 完整的修复说明和技术细节
- `docs/GROK_COOKIE_GUIDE.md` - Cookie 提取和使用指南

## 🔄 注入流程（新）

```
1. 初始化浏览器上下文
   ↓
2. 导航到目标域名 ⭐（建立域名上下文）
   ↓
3. 过滤已过期的 Cookie ⭐
   ↓
4. 规范化 Cookie 格式 ⭐
   ↓
5. 逐个注入 Cookie
   ↓
6. 重新加载页面 ⭐（应用 Cookie）
   ↓
7. 验证登录状态 ⭐（改进的验证逻辑）
   ↓
8. 保存 Session 信息
```

标记 ⭐ 的步骤是本次修复新增或改进的部分。

## ✨ 预期效果

修复后，Cookie 注入应该：
- ✅ 正确处理 Cookie 注入时机
- ✅ 自动过滤已过期的 Cookie
- ✅ 统一规范 Cookie 域名格式
- ✅ 准确验证登录状态
- ✅ 提供详细的日志和错误信息
- ✅ 大幅提高注入成功率

## 📞 支持

如果遇到问题：
1. 查看日志中的详细错误信息
2. 使用 `test_cookie_injection.py` 进行调试
3. 参考 `docs/COOKIE_INJECTION_FIX.md` 文档
4. 尝试重新提取新的 Cookie
