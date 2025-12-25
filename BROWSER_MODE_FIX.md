# 浏览器模式修复说明

## 问题
用户反馈浏览器在运行 Cookie 提取脚本时以"无痕模式"打开。

## 根本原因
1. Playwright 默认的 `new_context()` 会创建一个临时的、隔离的浏览器上下文，类似无痕模式的行为
2. 每次运行都会清空所有登录状态和 Cookie，导致用户每次都需要重新登录

## 解决方案

### 1. 使用持久化浏览器配置文件
修改了以下类以使用 `launch_persistent_context()` 而非 `launch()` + `new_context()`:
- `ManualOAuthExtractor` (services/cookie_extractor.py)
- `GrokCookieExtractor` (services/cookie_extractor.py)
- `SessionManager` (services/session_manager.py)

### 2. 配置更新
在 `config.py` 中添加：
- `GROK_OAUTH_USER_DATA_DIR`: 持久化数据目录路径
- `GROK_OAUTH_PERSISTENT_CONTEXT`: 启用/禁用持久化上下文

### 3. 浏览器参数
添加了以下浏览器启动参数以优化用户体验：
```python
launch_args = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-infobars",           # 禁用信息栏
    "--no-first-run",               # 跳过首次运行页面
    "--no-default-browser-check",   # 不检查默认浏览器
]
```

### 4. 用户反馈改进
更新了用户提示信息，明确说明：
- "浏览器已打开（正常模式，非无痕模式）"
- "浏览器使用持久化配置文件，登录信息会被保存"

## 技术细节

### 持久化上下文 vs 普通上下文

**普通上下文（旧方式）**:
```python
browser = await playwright.chromium.launch()
context = await browser.new_context()  # 每次都是全新的
```

**持久化上下文（新方式）**:
```python
context = await playwright.chromium.launch_persistent_context(
    user_data_dir="data/grok_oauth_profile"  # 保存到磁盘
)
```

### 目录结构
```
/home/engine/project/
├── data/
│   ├── grok_cookies.json             # 导出的 Cookie
│   └── grok_oauth_profile/            # 持久化浏览器配置文件
│       ├── Default/
│       │   ├── Cookies
│       │   ├── Local Storage/
│       │   └── ...
│       └── ...
└── sessions/
    ├── grok_cookie_extractor_profile/  # GrokCookieExtractor 的配置文件
    └── session_manager_profile/        # SessionManager 的配置文件
```

## 用户体验改进

### 首次运行
- 浏览器打开，用户完成 Google OAuth 登录
- 登录信息保存到持久化目录

### 后续运行
- 浏览器打开，**自动使用之前保存的登录状态**
- 用户无需重复登录（除非 Cookie 过期）

### 重置登录状态
如需清除保存的登录信息：
```bash
rm -rf data/grok_oauth_profile
```

## 配置选项

### 环境变量
可通过 `.env` 文件配置：
```bash
# 自定义浏览器数据目录
GROK_OAUTH_USER_DATA_DIR=/custom/path/to/profile

# 禁用持久化（恢复每次都全新环境）
GROK_OAUTH_PERSISTENT_CONTEXT=false

# 启用 headless 模式（不显示浏览器窗口）
GROK_HEADLESS_MODE=true
```

## 测试验证

### 验证持久化配置是否生效
1. 运行脚本：`python scripts/extract_grok_cookies.py`
2. 完成登录后，检查目录是否已创建：
   ```bash
   ls -la data/grok_oauth_profile/
   ```
3. 再次运行脚本，观察是否自动加载登录状态

### 验证不再是无痕模式
观察浏览器窗口：
- ✅ 地址栏左侧无"无痕模式"图标
- ✅ 窗口标题栏颜色为正常颜色（不是深色）
- ✅ 可以看到浏览器的本地数据（如已保存的密码提示）
- ✅ 第二次运行时，登录信息仍然保留

## 相关文件
- `services/cookie_extractor.py` - 核心提取逻辑
- `services/session_manager.py` - 会话管理
- `config.py` - 配置选项
- `docs/GROK_COOKIE_GUIDE.md` - 用户指南
- `tests/test_grok_cookies.py` - 单元测试

## 向后兼容性
- 默认启用持久化上下文（推荐）
- 可通过 `GROK_OAUTH_PERSISTENT_CONTEXT=false` 恢复旧行为
- 已有的 Cookie 文件格式保持不变
