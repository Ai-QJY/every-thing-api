# 本地 API 测试使用教程

这是一个快速上手指南，帮助你快速使用本地 API 测试工具来调用 Grok 等 AI 服务。

## 📋 前提条件

- Python 3.10 或更高版本
- Node.js（用于安装 Playwright 浏览器）
- 稳定的网络连接

## 🚀 快速开始（5 分钟）

### 1. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器（必须）
playwright install
```

### 2. 启动 API 服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动，你会看到：

```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. 测试服务是否正常

```bash
curl http://localhost:8000/
```

应该返回：
```json
{"message": "AI Browser Automation API Service"}
```

## 🔐 登录 Grok（必需）

使用前需要先登录 Grok，有两种方式：

### 方式一：一键自动登录（推荐）

使用你的 Grok 账号自动登录并创建会话：

```bash
curl -X POST http://localhost:8000/api/session/grok-login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your_email@example.com",
    "password": "your_password"
  }'
```

**返回示例：**
```json
{
  "status": "success",
  "message": "Grok login and session creation successful",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "cookie_count": 11,
  "extracted_at": "2024-01-15T10:30:00"
}
```

### 方式二：手动注入 Cookies

如果你已经有 Grok 的 cookies，可以直接注入：

```bash
curl -X POST http://localhost:8000/api/session/inject-cookies \
  -H "Content-Type: application/json" \
  -d '{
    "cookies": [
      {
        "name": "your_cookie_name",
        "value": "your_cookie_value",
        "domain": ".grok.com",
        "path": "/",
        "httpOnly": true,
        "secure": true
      }
    ]
  }'
```

### 检查登录状态

```bash
curl http://localhost:8000/api/session/status
```

**返回示例：**
```json
{
  "logged_in": true,
  "session_valid": true,
  "session_expiry": "2024-01-16T10:30:00Z",
  "browser_type": "chromium"
}
```

## 🎨 使用 API 生成图片

登录成功后，就可以调用图片生成接口了：

```bash
curl -X POST http://localhost:8000/api/grok/image \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "一只赛博朋克风格的猫，霓虹灯光"
  }'
```

**返回示例：**
```json
{
  "success": true,
  "file_path": "/home/engine/project/output/grok_image_20240115_103045_abc123.png",
  "file_type": "image"
}
```

图片会自动保存到 `output` 目录。

## 📝 使用 Python 测试

### 基础测试

```bash
python test_basic.py
```

这会测试基本的 API 功能。

### 简单测试

```bash
python simple_test.py
```

这会检查项目结构和配置是否正确。

## 🔧 配置说明

编辑 `config.py` 可以修改以下设置：

```python
# 浏览器配置
BROWSER_TYPE = "chromium"  # 浏览器类型
HEADLESS = False          # 是否无头模式（False 可见浏览器窗口）

# API 配置
API_HOST = "0.0.0.0"      # API 监听地址
API_PORT = 8000          # API 端口

# 超时设置
GENERATION_TIMEOUT = 300  # 图片生成超时（秒）
LOGIN_TIMEOUT = 120      # 登录超时（秒）

# 文件存储
OUTPUT_DIR = "/home/engine/project/output"      # 输出目录
SESSION_DIR = "/home/engine/project/sessions"   # 会话目录
```

## 📊 完整测试流程示例

```bash
# 1. 启动服务
python main.py &

# 2. 等待服务启动（2-3秒）
sleep 3

# 3. 登录 Grok
curl -X POST http://localhost:8000/api/session/grok-login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your_email@example.com",
    "password": "your_password"
  }'

# 4. 检查登录状态
curl http://localhost:8000/api/session/status

# 5. 生成图片
curl -X POST http://localhost:8000/api/grok/image \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "一只可爱的卡通狗，彩虹色"
  }'

# 6. 查看生成的图片
ls -lh output/
```

## ⚠️ 常见问题

### 问题 1：安装 Playwright 失败

```bash
# 尝试重装
pip install --upgrade playwright
playwright install --force chromium
```

### 问题 2：登录失败，提示"No valid session"

- 确认你已经先调用了 `/api/session/grok-login`
- 检查账号密码是否正确
- 确认网络可以访问 grok.com

### 问题 3：生成图片超时

- 在 `config.py` 中增加 `GENERATION_TIMEOUT` 的值
- 检查网络连接是否稳定

### 问题 4：浏览器不显示

- 确保 `HEADLESS = False`
- Linux 系统可能需要设置 `DISPLAY` 环境变量：
  ```bash
  export DISPLAY=:0
  python main.py
  ```

### 问题 5：Cookie 注入失败

- 确保 cookies 来自有效的 Grok 登录会话
- 检查 cookies 是否已过期
- 查看控制台日志获取详细错误信息

## 🔍 调试技巧

### 查看详细日志

服务启动时会打印详细日志，注意观察：
- `INFO` - 正常操作信息
- `ERROR` - 错误信息
- `WARNING` - 警告信息

### 使用浏览器开发者工具

登录 Grok 时，浏览器窗口会显示，你可以：
- 手动检查登录是否成功
- 使用 F12 打开开发者工具查看 cookies
- 查看网络请求

### 清空会话重新开始

```bash
# 清空会话目录
rm -rf sessions/*

# 重新登录
curl -X POST http://localhost:8000/api/session/grok-login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your_email@example.com",
    "password": "your_password"
  }'
```

## 📖 API 接口列表

### Session 管理接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/session/status` | GET | 检查登录状态 |
| `/api/session/grok-login` | POST | Grok 一键登录 |
| `/api/session/inject-cookies` | POST | 注入 Cookies |
| `/api/session/logout` | POST | 退出登录 |
| `/api/session/extract-grok-cookies` | POST | 提取 Grok Cookies |

### Grok 生成接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/grok/image` | POST | 生成图片 |
| `/api/grok/video` | POST | 生成视频（未实现）|

## 🎯 最佳实践

1. **首次使用**：先运行 `python simple_test.py` 确保环境正常
2. **测试登录**：登录后立即调用 `/api/session/status` 确认会话有效
3. **保存 Cookies**：成功登录后，cookies 会自动保存到文件，重启服务无需重新登录
4. **监控生成**：生成图片时注意观察日志，确认生成进度
5. **处理超时**：遇到超时，先检查网络，再考虑增加超时时间

## 📞 获取帮助

- 查看服务日志获取详细错误信息
- 检查 `docs/` 目录下的详细文档
- 确保 Playwright 浏览器已正确安装

## 📝 注意事项

1. **Cookie 有效期**：Grok 的 cookies 有限期（通常 2-24 小时），过期后需要重新登录
2. **网络要求**：需要能够访问 grok.com，请确保网络稳定
3. **资源占用**：浏览器会占用较多内存，建议有至少 4GB 可用内存
4. **并发限制**：当前版本不支持并发请求，请等待上一个请求完成后再发送新请求
5. **浏览器窗口**：首次登录会弹出浏览器窗口，请勿关闭

---

祝你使用愉快！如有问题请查看控制台日志或检查配置文件。
