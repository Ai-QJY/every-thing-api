# Grok Cookie Extraction Guide

本指南介绍如何使用半自动化工具提取 Grok.com 的登录 Cookie。

## 目录

- [快速开始](#快速开始)
- [命令行使用](#命令行使用)
- [API 使用](#api-使用)
- [Python SDK 使用](#python-sdk-使用)
- [Cookie 有效期说明](#cookie-有效期说明)
- [常见问题排查](#常见问题排查)
- [代码示例](#代码示例)

---

## 快速开始

### 1. 安装依赖

```bash
pip install playwright
playwright install chromium
```

### 2. 运行提取脚本

```bash
python scripts/extract_grok_cookies.py
```

脚本会自动：
1. 打开浏览器窗口显示 grok.com
2. 等待你完成 Google OAuth 登录
3. 自动导出并保存 Cookie

---

## 命令行使用

### 基本用法

```bash
python scripts/extract_grok_cookies.py
```

### 自定义超时时间

```bash
# 设置 5 分钟超时
python scripts/extract_grok_cookies.py --timeout 300

# 简写形式
python scripts/extract_grok_cookies.py -t 600
```

### 自定义输出文件

```bash
python scripts/extract_grok_cookies.py --output /path/to/my_cookies.json
```

### 启用详细日志

```bash
python scripts/extract_grok_cookies.py --verbose
```

### 输出示例

```
============================================================
  🐸 Grok Cookie Extraction Tool (Manual OAuth)
============================================================

🚀 启动半自动化 Cookie 提取流程...
   目标网站：https://grok.com
   超时设置：600 秒
   输出文件：data/grok_cookies.json

============================================================
✅ 浏览器已打开
⏳ 请在浏览器中完成以下步骤：
   1. 点击 'Sign in with Google' 按钮
   2. 使用 Google 账号登录
   3. 点击 'Authorize' 或 '同意' 按钮授权
   4. 等待页面加载完成

⏰ 等待超时时间：600 秒（10 分钟）

📌 提示：
   - 登录完成后，Cookie 将自动导出
   - 可以随时按 Ctrl+C 中止操作
============================================================

✅ 成功完成！
   📊 导出 Cookie 数量：15
   💾 保存路径：data/grok_cookies.json
   ⏱️  用时：45.32 秒
```

---

## API 使用

### 1. 触发半自动提取

启动浏览器并等待用户完成登录：

```bash
curl -X POST http://localhost:8000/api/session/extract-grok-cookies-manual \
  -H "Content-Type: application/json" \
  -d '{"timeout": 600}'
```

**响应：**

```json
{
  "status": "waiting_for_login",
  "message": "浏览器已启动，请完成 Google 登录授权...",
  "task_id": "abc123-def456-ghi789",
  "timeout_seconds": 600
}
```

### 2. 检查提取状态

使用返回的 `task_id` 查询进度：

```bash
curl http://localhost:8000/api/session/extract-grok-status/abc123-def456-ghi789
```

**响应（进行中）：**

```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "waiting_for_login"
}
```

**响应（完成）：**

```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "completed",
  "cookies_count": 15,
  "extracted_at": "2025-12-24T10:30:00Z",
  "duration_seconds": 45.32
}
```

**响应（失败）：**

```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "failed",
  "error_message": "Login timed out after 600 seconds"
}
```

### 3. 注入已导出的 Cookie

将之前提取的 Cookie 注入到会话中：

```bash
curl -X POST http://localhost:8000/api/session/inject-grok-cookies \
  -H "Content-Type: application/json" \
  -d '{
    "cookies": [
      {
        "name": "APISID",
        "value": "your_cookie_value",
        "domain": ".google.com",
        "path": "/",
        "expires": 1735171200,
        "httpOnly": true,
        "secure": true,
        "sameSite": "None"
      }
    ],
    "remember_me": true
  }'
```

**响应：**

```json
{
  "status": "success",
  "message": "Cookies injected successfully",
  "session_id": "xyz789-abc123",
  "cookies_count": 15,
  "saved_to": "data/grok_cookies.json"
}
```

### 4. 加载已保存的 Cookie

```bash
curl http://localhost:8000/api/session/load-grok-cookies
```

**响应：**

```json
{
  "status": "success",
  "message": "Loaded 15 cookies",
  "cookies": [...],
  "cookie_count": 15
}
```

---

## Python SDK 使用

### 基本用法

```python
import asyncio
from services.cookie_extractor import extract_grok_cookies_with_manual_oauth

async def main():
    # 提取 Cookie（会打开浏览器窗口）
    result = await extract_grok_cookies_with_manual_oauth(timeout=600)
    
    if result["status"] == "success":
        print(f"成功导出 {result['cookie_count']} 个 Cookie")
        print(f"保存到: {result['saved_to']}")
    else:
        print(f"提取失败: {result.get('error_message')}")

asyncio.run(main())
```

### 保存和加载 Cookie

```python
from services.cookie_extractor import save_cookies_to_file, load_cookies_from_file

# 保存 Cookie 到文件
save_path = save_cookies_to_file(cookies, "my_grok_cookies.json")

# 从文件加载 Cookie
cookies = load_cookies_from_file("my_grok_cookies.json")
```

### 使用 ManualOAuthExtractor 类

```python
from services.cookie_extractor import ManualOAuthExtractor

async def extract_with_progress():
    extractor = ManualOAuthExtractor()
    
    result = await extractor.extract_with_manual_oauth(timeout=300)
    
    if result["status"] == "success":
        print(f"✅ 成功导出 {result['cookie_count']} 个 Cookie")
        print(f"📁 保存到: {result['saved_to']}")
    
    return result
```

---

## Cookie 有效期说明

### 有效期范围

Grok Cookie 的有效期通常为：
- **短期 Cookie**：几小时到几天
- **长期 Cookie**：几周到几个月
- **刷新 Token**：通常 1-6 个月

### 影响因素

1. **Google 账户设置**：账户的安全级别会影响 Token 有效期
2. **登录方式**：OAuth 授权比直接登录的有效期通常更长
3. **使用频率**：频繁使用会延长 Cookie 有效期
4. **设备信任**：可信设备的 Cookie 有效期更长

### 最佳实践

- 定期重新提取 Cookie 以确保有效性
- 保存多个 Cookie 副本以备不时之需
- 关注 Cookie 过期时间，及时刷新

---

## 常见问题排查

### 问题 1：浏览器无法启动

**错误信息：**
```
Error: Chromium browser not found
```

**解决方案：**
```bash
# 安装 Playwright 浏览器
playwright install chromium

# 或安装所有浏览器
playwright install
```

### 问题 2：浏览器看起来像无痕/每次都要重新登录

**说明：**
手动 OAuth 模式默认使用一个 **持久化** 的浏览器用户数据目录（`data/grok_oauth_profile`），用于保存登录状态，避免每次都像“无痕/访客”一样重新登录。

**解决方案：**
1. 首次运行请完成一次 Google 登录，之后会自动复用登录状态
2. 想“重置”登录状态：删除 `data/grok_oauth_profile` 目录
3. 想自定义浏览器数据目录：设置环境变量 `GROK_OAUTH_USER_DATA_DIR`
4. 想关闭持久化（每次都全新环境）：设置 `GROK_OAUTH_PERSISTENT_CONTEXT=false`

### 问题 3：登录后 Cookie 未导出

**可能原因：**
1. 页面 URL 未正确变化
2. 用户在登录过程中中断
3. 网络问题导致 Cookie 未同步

**解决方案：**
1. 等待页面完全加载后再操作
2. 确保完成整个 OAuth 流程
3. 检查网络连接

### 问题 4：Cookie 注入后无法使用

**可能原因：**
1. Cookie 已过期
2. Cookie 域名不匹配
3. 安全设置导致 Cookie 无效

**解决方案：**
1. 重新提取最新的 Cookie
2. 检查 Cookie 的 domain 字段
3. 确保使用相同的浏览器配置

### 问题 5：超时时间设置不合理

**建议设置：**
- **首次登录**：600 秒（10 分钟）
- **后续登录**：300 秒（5 分钟）
- **快速测试**：120 秒（2 分钟）

### 问题 6：API 返回 404 Task not found

**可能原因：**
1. task_id 已过期
2. task_id 输入错误
3. 任务已被清理

**解决方案：**
1. 重新触发提取获取新的 task_id
2. 确保正确复制 task_id

---

## 代码示例

### cURL 完整流程

```bash
#!/bin/bash
# Grok Cookie 提取完整流程

API_BASE="http://localhost:8000/api/session"

echo "🚀 开始 Grok Cookie 提取流程..."

# 1. 触发提取
echo "📡 触发浏览器..."
RESPONSE=$(curl -s -X POST "$API_BASE/extract-grok-cookies-manual" \
  -H "Content-Type: application/json" \
  -d '{"timeout": 600}')

echo "响应: $RESPONSE"

# 提取 task_id
TASK_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])")
echo "📋 Task ID: $TASK_ID"

# 2. 等待用户登录完成
echo "⏳ 请在浏览器中完成登录..."
echo "   完成登录后，按 Enter 键继续查询状态..."
read

# 3. 检查状态
while true; do
    STATUS=$(curl -s "$API_BASE/extract-grok-status/$TASK_ID" | \
        python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
    
    echo "📊 当前状态: $STATUS"
    
    if [ "$STATUS" == "completed" ]; then
        echo "✅ 提取完成！"
        break
    elif [ "$STATUS" == "failed" ] || [ "$STATUS" == "cancelled" ]; then
        echo "❌ 提取失败或已取消"
        break
    fi
    
    sleep 5
done

# 4. 加载 Cookie
echo "📂 加载 Cookie..."
curl -s "$API_BASE/load-grok-cookies"
echo ""
```

### Python 完整流程

```python
#!/usr/bin/env python3
"""
Grok Cookie 提取完整流程示例
"""

import asyncio
import aiohttp
from services.cookie_extractor import (
    extract_grok_cookies_with_manual_oauth,
    save_cookies_to_file,
    load_cookies_from_file
)
from api.routers.session import CookieInjectionRequestV2, Cookie


async def run_extraction_and_inject():
    """执行提取并注入 Cookie"""
    
    # 方法 1：使用脚本提取（推荐）
    print("=" * 50)
    print("推荐使用命令行工具：")
    print("  python scripts/extract_grok_cookies.py")
    print("=" * 50)
    
    # 方法 2：使用 API
    API_BASE = "http://localhost:8000/api/session"
    
    # 触发提取
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_BASE}/extract-grok-cookies-manual",
            json={"timeout": 600}
        ) as resp:
            result = await resp.json()
            task_id = result["task_id"]
            print(f"任务已创建: {task_id}")
            
            # 轮询状态
            while True:
                await asyncio.sleep(5)
                async with session.get(
                    f"{API_BASE}/extract-grok-status/{task_id}"
                ) as status_resp:
                    status_data = await status_resp.json()
                    print(f"状态: {status_data['status']}")
                    
                    if status_data["status"] == "completed":
                        break
    
    # 加载并注入 Cookie
    cookies = load_cookies_from_file()
    print(f"已加载 {len(cookies)} 个 Cookie")
    
    return cookies


async def main():
    """主函数"""
    try:
        # 提取并注入
        cookies = await run_extraction_and_inject()
        
        print("\n✅ 流程完成！")
        print(f"共 {len(cookies)} 个 Cookie")
        
    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 注意事项

1. **安全性**：Cookie 包含敏感信息，请妥善保管
2. **隐私**：确保在安全的网络环境中操作
3. **合规**：仅提取您有权访问的账户 Cookie
4. **维护**：定期更新 Cookie 以确保持续访问

---

## 获取帮助

如遇到问题，请：
1. 检查本指南的[常见问题排查](#常见问题排查)部分
2. 查看日志文件获取详细错误信息
3. 联系技术支持团队
