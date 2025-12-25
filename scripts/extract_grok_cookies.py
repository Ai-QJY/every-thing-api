#!/usr/bin/env python3
"""
Grok Cookie Extraction Script - Semi-Automated OAuth Flow

This script launches a visible browser window and waits for the user
to manually complete the Google OAuth login process for Grok.com.

Usage:
    python scripts/extract_grok_cookies.py [--timeout 600]

The script will:
1. Open a browser window showing grok.com
2. Wait for you to complete Google OAuth login
3. Automatically export all cookies when login is detected
4. Save cookies to data/grok_cookies.json

Press Ctrl+C at any time to abort the operation.
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.cookie_extractor import (
    extract_grok_cookies_with_manual_oauth,
    save_cookies_to_file,
    load_cookies_from_file
)
from config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print welcome banner"""
    print("\n" + "=" * 60)
    print("  🐸 Grok Cookie Extraction Tool (Manual OAuth)")
    print("=" * 60)
    print()


def print_result(result: dict):
    """Print extraction result in a formatted way"""
    status = result.get("status", "unknown")
    
    if status == "success":
        print("\n✅ 成功完成！")
        print(f"   📊 导出 Cookie 数量：{result.get('cookie_count', 0)}")
        print(f"   💾 保存路径：{result.get('saved_to', 'N/A')}")
        print(f"   ⏱️  用时：{result.get('duration_seconds', 0)} 秒")
        print(f"   🕐 完成时间：{result.get('extracted_at', 'N/A')}")
    elif status == "cancelled":
        print("\n⚠️  操作已取消")
        print(f"   原因：{result.get('error_message', 'User interrupted')}")
    elif status == "error":
        print("\n❌ 提取失败！")
        print(f"   错误类型：{result.get('error_type', 'unknown')}")
        print(f"   错误信息：{result.get('error_message', 'Unknown error')}")
    else:
        print(f"\n⚠️  未知状态：{status}")
        print(f"   详情：{result}")
    
    print()


async def main():
    """Main entry point"""
    print_banner()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Extract Grok cookies with manual OAuth login"
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=config.GROK_OAUTH_TIMEOUT,
        help=f"Timeout in seconds (default: {config.GROK_OAUTH_TIMEOUT})"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Custom output file path"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Ensure data directory exists
    Path(config.GROK_COOKIE_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    print("🚀 启动半自动化 Cookie 提取流程...")
    print(f"   目标网站：{config.GROK_URL}")
    print(f"   超时设置：{args.timeout} 秒")
    print(f"   输出文件：{args.output or config.GROK_COOKIE_FILE_PATH}")
    print()
    
    try:
        # Run the extraction
        result = await extract_grok_cookies_with_manual_oauth(
            timeout_seconds=args.timeout
        )
        
        # Print result
        print_result(result)
        
        # If successful, also try to load and show sample cookies
        if result.get("status") == "success":
            print("📋 Cookie 样本（前 5 个）：")
            print("-" * 50)
            cookies = result.get("cookies", [])
            for i, cookie in enumerate(cookies[:5], 1):
                print(f"   {i}. {cookie.get('name', 'N/A')}")
                print(f"      Domain: {cookie.get('domain', 'N/A')}")
                print(f"      Value: {cookie.get('value', 'N/A')[:50]}...")
                print()
            
            if len(cookies) > 5:
                print(f"   ... 还有 {len(cookies) - 5} 个 Cookie")
            
            print("\n💡 使用提示：")
            print("   - Cookie 已保存到文件，可用于 API 认证")
            print("   - 使用 inject-grok-cookies API 注入 Cookie")
            print("   - Cookie 有效期通常为几天到几周")
        
        return result
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        print("   如需重新运行，请执行：python scripts/extract_grok_cookies.py")
        return {"status": "cancelled", "error_message": "User interrupted"}
    
    except Exception as e:
        logger.exception("Unexpected error during extraction")
        print(f"\n❌ 发生意外错误：{str(e)}")
        return {"status": "error", "error_type": "unexpected", "error_message": str(e)}


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result.get("status") == "success" else 1)
