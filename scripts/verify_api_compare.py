#!/usr/bin/env python3
"""Ping API 比选各 provider（不暴露完整 key）。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api_compare_env import (  # noqa: E402
    load_api_compare_env,
    print_verify_report,
    verify_api_compare,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="验证 API 比选密钥连通性")
    parser.add_argument(
        "--no-pro",
        action="store_true",
        help="跳过 deepseek-v4-pro",
    )
    args = parser.parse_args()

    env_path = load_api_compare_env()
    results = verify_api_compare(include_pro=not args.no_pro)
    fails = print_verify_report(results, env_path=env_path)
    raise SystemExit(1 if fails else 0)


if __name__ == "__main__":
    main()
