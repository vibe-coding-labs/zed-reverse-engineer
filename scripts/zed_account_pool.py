#!/usr/bin/env python3
"""
Zed 账号池管理
==============
加密存储 Zed 账号凭证，支持多账号管理、有效性验证、自动切换。

安全设计:
- Token 使用 Fernet (AES-128-CBC + HMAC-SHA256) 加密存储
- 加密密钥存储在单独的文件中，权限 600
- 数据库文件权限 600
- 内存中的 token 使用完毕后立即释放

用法:
  # 添加账号
  python3 scripts/zed_account_pool.py add --user-id 12345 --token "xxx"

  # 列出账号
  python3 scripts/zed_account_pool.py list

  # 验证账号
  python3 scripts/zed_account_pool.py verify --user-id 12345

  # 验证所有账号
  python3 scripts/zed_account_pool.py verify-all

  # 删除账号
  python3 scripts/zed_account_pool.py remove --user-id 12345
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("zed_account_pool")

# ============================================================================
# 配置
# ============================================================================

POOL_DIR = Path.home() / ".zed-account-pool"
DB_PATH = POOL_DIR / "pool.db"
KEY_PATH = POOL_DIR / ".encryption_key"
CLOUD_API = "https://cloud.zed.dev"


# ============================================================================
# 加密工具
# ============================================================================

def _ensure_pool_dir():
    """创建池目录，权限 700"""
    POOL_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)


def _load_or_create_key() -> bytes:
    """加载或创建加密密钥。密钥文件权限 600"""
    _ensure_pool_dir()
    if KEY_PATH.exists():
        # 权限检查
        current_mode = os.stat(KEY_PATH).st_mode & 0o777
        if current_mode != 0o600:
            logger.warning(f"密钥文件权限不正确 ({oct(current_mode)}，应为 600)，正在修正")
            KEY_PATH.chmod(0o600)
        return KEY_PATH.read_bytes()

    key = Fernet.generate_key()
    # 原子写入：先写临时文件再 rename
    tmp_path = KEY_PATH.with_suffix(".tmp")
    tmp_path.write_bytes(key)
    tmp_path.chmod(0o600)
    tmp_path.rename(KEY_PATH)
    logger.info(f"已生成加密密钥: {KEY_PATH}")
    return key


def _get_cipher() -> Fernet:
    """获取加密器实例"""
    key = _load_or_create_key()
    return Fernet(key)


def encrypt_token(plaintext: str) -> str:
    """加密 token，返回 base64 密文字符串"""
    cipher = _get_cipher()
    return cipher.encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """解密 token，返回明文"""
    cipher = _get_cipher()
    return cipher.decrypt(ciphertext.encode()).decode()


# ============================================================================
# 数据库操作
# ============================================================================

def _get_conn() -> sqlite3.Connection:
    """获取数据库连接（自动创建表）"""
    _ensure_pool_dir()
    DB_PATH.touch(mode=0o600, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection):
    """初始化数据库表结构"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            user_id          INTEGER NOT NULL PRIMARY KEY,
            nickname         TEXT NOT NULL DEFAULT '',
            remark           TEXT NOT NULL DEFAULT '',
            access_token     TEXT NOT NULL,          -- Fernet 加密
            github_login     TEXT NOT NULL DEFAULT '',
            plan             TEXT NOT NULL DEFAULT 'unknown',
            is_valid         INTEGER NOT NULL DEFAULT 0,
            last_verified_at TEXT,
            trial_started_at TEXT,
            is_account_too_young INTEGER NOT NULL DEFAULT 0,
            edit_predictions_used   INTEGER NOT NULL DEFAULT 0,
            edit_predictions_limit  TEXT NOT NULL DEFAULT '2000',
            organizations    TEXT NOT NULL DEFAULT '[]',
            default_org_id   TEXT,
            display_order    INTEGER NOT NULL DEFAULT 0,
            created_at       TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS settings (
            key        TEXT NOT NULL PRIMARY KEY,
            value      TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()


# ============================================================================
# 账号操作
# ============================================================================

def add_account(
    user_id: int,
    access_token: str,
    nickname: str = "",
    remark: str = "",
    github_login: str = "",
    plan: str = "unknown",
    is_valid: bool = False,
    organizations: list = None,
    default_org_id: str = None,
) -> bool:
    """
    添加账号到池中。token 会被加密存储。
    如果 user_id 已存在则更新。
    """
    encrypted = encrypt_token(access_token)

    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO accounts (user_id, nickname, remark, access_token, github_login,
                                  plan, is_valid, organizations, default_org_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                access_token       = excluded.access_token,
                nickname           = excluded.nickname,
                remark             = excluded.remark,
                github_login       = excluded.github_login,
                plan               = excluded.plan,
                is_valid           = excluded.is_valid,
                organizations      = excluded.organizations,
                default_org_id     = excluded.default_org_id,
                updated_at         = datetime('now')
        """, (
            user_id, nickname, remark, encrypted, github_login,
            plan, 1 if is_valid else 0,
            json.dumps(organizations or []), default_org_id,
        ))
        conn.commit()
        logger.info(f"✅ 账号 {user_id} ({github_login or nickname}) 已{'添加' if 'ON CONFLICT' in '' else '更新'}")
        return True
    except sqlite3.Error as e:
        logger.error(f"❌ 添加账号失败: {e}")
        return False
    finally:
        conn.close()


def remove_account(user_id: int) -> bool:
    """从池中删除账号"""
    conn = _get_conn()
    try:
        cursor = conn.execute("DELETE FROM accounts WHERE user_id = ?", (user_id,))
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"✅ 账号 {user_id} 已删除")
            return True
        else:
            logger.warning(f"⚠️ 账号 {user_id} 不存在")
            return False
    except sqlite3.Error as e:
        logger.error(f"❌ 删除失败: {e}")
        return False
    finally:
        conn.close()


def list_accounts(show_token: bool = False) -> list:
    """列出所有账号（默认不显示 token）"""
    conn = _get_conn()
    try:
        cursor = conn.execute("""
            SELECT user_id, nickname, remark, access_token, github_login, plan,
                   is_valid, last_verified_at, display_order, created_at
            FROM accounts ORDER BY display_order, user_id
        """)
        accounts = []
        for row in cursor.fetchall():
            acct = dict(row)
            if show_token:
                try:
                    acct["access_token"] = decrypt_token(acct["access_token"])
                except Exception:
                    acct["access_token"] = "<解密失败>"
            else:
                acct["access_token"] = acct["access_token"][:20] + "..." if len(acct["access_token"]) > 20 else "<加密存储>"
            accounts.append(acct)
        return accounts
    finally:
        conn.close()


def get_account(user_id: int, decrypt: bool = True) -> Optional[dict]:
    """获取单个账号信息"""
    conn = _get_conn()
    try:
        cursor = conn.execute("SELECT * FROM accounts WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        acct = dict(row)
        if decrypt:
            try:
                acct["access_token"] = decrypt_token(acct["access_token"])
            except Exception:
                acct["access_token"] = None
        return acct
    finally:
        conn.close()


def get_all_accounts_with_tokens() -> list:
    """获取所有账号及其解密后的 token（供代理使用）"""
    conn = _get_conn()
    try:
        cursor = conn.execute("""
            SELECT user_id, access_token, github_login, plan, default_org_id
            FROM accounts WHERE is_valid = 1 ORDER BY display_order, user_id
        """)
        accounts = []
        for row in cursor.fetchall():
            acct = dict(row)
            try:
                acct["access_token"] = decrypt_token(acct["access_token"])
                accounts.append(acct)
            except Exception:
                logger.warning(f"账号 {acct['user_id']} token 解密失败，跳过")
        return accounts
    finally:
        conn.close()


# ============================================================================
# 账号验证
# ============================================================================

def verify_account(user_id: int) -> bool:
    """
    验证单个账号是否有效。
    通过调用 cloud.zed.dev 的 /client/users/me 端点验证。
    """
    acct = get_account(user_id, decrypt=True)
    if acct is None:
        logger.warning(f"⚠️ 账号 {user_id} 不存在")
        return False

    import urllib.request
    import urllib.error

    token = acct.get("access_token")
    if not token:
        logger.warning(f"⚠️ 账号 {user_id} token 为空")
        return False

    try:
        req = urllib.request.Request(
            f"{CLOUD_API}/client/users/me",
            headers={
                "Authorization": f"{user_id} {token}",
                "Content-Type": "application/json",
                "User-Agent": "Zed-Account-Pool/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        # 解析响应
        user = data.get("user", {})
        plan_info = data.get("plan", {})
        plan_v3 = plan_info.get("plan_v3", "unknown")
        if isinstance(plan_v3, dict):
            plan_v3 = plan_v3.get("known", "unknown")

        orgs = data.get("organizations", [])
        default_org = data.get("default_organization_id", {})
        if isinstance(default_org, dict):
            default_org = default_org.get("0")

        usage = plan_info.get("usage", {})
        edit_pred = usage.get("edit_predictions", {})

        # 更新数据库
        conn = _get_conn()
        conn.execute("""
            UPDATE accounts SET
                github_login = ?,
                plan = ?,
                is_valid = 1,
                last_verified_at = datetime('now'),
                trial_started_at = ?,
                is_account_too_young = ?,
                edit_predictions_used = ?,
                edit_predictions_limit = ?,
                organizations = ?,
                default_org_id = ?,
                updated_at = datetime('now')
            WHERE user_id = ?
        """, (
            user.get("github_login", ""),
            plan_v3,
            plan_info.get("trial_started_at"),
            1 if plan_info.get("is_account_too_young", False) else 0,
            edit_pred.get("used", 0),
            str(edit_pred.get("limit", "2000")),
            json.dumps([{"id": o.get("id", {}).get("0", ""), "name": o.get("name", "")} for o in orgs]),
            default_org,
            user_id,
        ))
        conn.commit()
        conn.close()

        logger.info(f"✅ 账号 {user_id} ({user.get('github_login', '')}) 有效")
        logger.info(f"   Plan: {plan_v3}")
        logger.info(f"   Trial: {plan_info.get('trial_started_at', 'N/A')}")
        return True

    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        status = e.code
        is_valid = False

        # 401 = token 无效，标记为无效
        if status == 401:
            logger.warning(f"❌ 账号 {user_id} token 无效 (401)")
        elif status == 402:
            logger.warning(f"⚠️ 账号 {user_id} 需要付费 (402): {body}")
            is_valid = True  # token 有效但 plan 受限
        else:
            logger.warning(f"⚠️ 账号 {user_id} HTTP {status}: {body}")

        # 更新状态
        conn = _get_conn()
        conn.execute("""
            UPDATE accounts SET is_valid = ?, last_verified_at = datetime('now'), updated_at = datetime('now')
            WHERE user_id = ?
        """, (1 if is_valid else 0, user_id))
        conn.commit()
        conn.close()
        return is_valid

    except Exception as e:
        logger.error(f"❌ 账号 {user_id} 验证失败: {e}")
        return False


def verify_all_accounts():
    """验证池中所有账号"""
    conn = _get_conn()
    cursor = conn.execute("SELECT user_id FROM accounts ORDER BY display_order, user_id")
    user_ids = [row["user_id"] for row in cursor.fetchall()]
    conn.close()

    valid = 0
    invalid = 0
    total = len(user_ids)

    logger.info(f"\n开始验证 {total} 个账号...")
    for uid in user_ids:
        if verify_account(uid):
            valid += 1
        else:
            invalid += 1

    logger.info(f"\n验证完成: {valid}/{total} 有效, {invalid}/{total} 无效")
    return valid, invalid, total


# ============================================================================
# 统计信息
# ============================================================================

def pool_stats() -> dict:
    """获取账号池统计信息"""
    conn = _get_conn()
    try:
        cursor = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(is_valid) as valid,
                SUM(CASE WHEN plan = 'zed_pro' OR plan = 'zed_pro_trial' THEN 1 ELSE 0 END) as pro_count,
                SUM(CASE WHEN plan = 'zed_free' THEN 1 ELSE 0 END) as free_count,
                SUM(CASE WHEN plan = 'zed_business' THEN 1 ELSE 0 END) as business_count
            FROM accounts
        """)
        stats = dict(cursor.fetchone())

        # 统计最近验证
        cursor = conn.execute("""
            SELECT last_verified_at FROM accounts
            WHERE last_verified_at IS NOT NULL
            ORDER BY last_verified_at DESC LIMIT 1
        """)
        row = cursor.fetchone()
        stats["last_verification"] = row["last_verified_at"] if row else None

        return stats
    finally:
        conn.close()


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Zed 账号池管理")
    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="添加账号")
    p_add.add_argument("--user-id", type=int, required=True, help="Zed 用户 ID")
    p_add.add_argument("--token", required=True, help="access_token")
    p_add.add_argument("--nickname", default="", help="昵称")
    p_add.add_argument("--remark", default="", help="备注")
    p_add.add_argument("--verify", action="store_true", help="添加后立即验证")

    # remove
    p_rm = sub.add_parser("remove", help="删除账号")
    p_rm.add_argument("--user-id", type=int, required=True, help="Zed 用户 ID")

    # list
    sub.add_parser("list", help="列出所有账号")
    p_list = sub.add_parser("list", help="列出账号")
    p_list.add_argument("--show-token", action="store_true", help="显示解密后的 token（危险！）")

    # verify
    p_verify = sub.add_parser("verify", help="验证单个账号")
    p_verify.add_argument("--user-id", type=int, required=True, help="Zed 用户 ID")

    # verify-all
    sub.add_parser("verify-all", help="验证所有账号")

    # stats
    sub.add_parser("stats", help="账号池统计")

    # export
    p_export = sub.add_parser("export", help="导出可用账号（供代理使用）")
    p_export.add_argument("--format", choices=["json", "env"], default="json")

    args = parser.parse_args()

    if args.command == "add":
        add_account(args.user_id, args.token, nickname=args.nickname, remark=args.remark)
        if args.verify:
            verify_account(args.user_id)

    elif args.command == "remove":
        remove_account(args.user_id)

    elif args.command == "list":
        accounts = list_accounts(show_token=args.show_token)
        if not accounts:
            logger.info("账号池为空")
            return
        logger.info(f"\n共 {len(accounts)} 个账号:")
        logger.info(f"{'ID':>8} {'昵称':<16} {'GitHub':<24} {'Plan':<16} {'有效':>4} {'验证时间':<22}")
        logger.info("-" * 100)
        for a in accounts:
            valid = "✅" if a["is_valid"] else "❌"
            verified = a.get("last_verified_at", "") or "未验证"
            logger.info(f"{a['user_id']:>8} {a['nickname']:<16} {a['github_login']:<24} {a['plan']:<16} {valid:>4} {verified:<22}")

    elif args.command == "verify":
        verify_account(args.user_id)

    elif args.command == "verify-all":
        verify_all_accounts()

    elif args.command == "stats":
        stats = pool_stats()
        logger.info(f"\n账号池统计:")
        logger.info(f"  总账号: {stats['total']}")
        logger.info(f"  有效:   {stats['valid']}")
        logger.info(f"  Pro:    {stats['pro_count']} (含试用)")
        logger.info(f"  Free:   {stats['free_count']}")
        logger.info(f"  企业:   {stats['business_count']}")
        logger.info(f"  最近验证: {stats.get('last_verification', '从未')}")

    elif args.command == "export":
        accounts = get_all_accounts_with_tokens()
        if args.format == "json":
            print(json.dumps(accounts, indent=2, ensure_ascii=False))
        elif args.format == "env":
            for a in accounts:
                print(f"ZED_USER_ID={a['user_id']}")
                print(f"ZED_ACCESS_TOKEN={a['access_token']}")
                print("---")


if __name__ == "__main__":
    main()