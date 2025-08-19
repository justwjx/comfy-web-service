#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量为 LoRA 元数据文件添加/合并 tips 字段（不会覆盖已有触发词）。

支持文件：*.json、*.civitai.info
默认扫描目录：
  - /home/wjx/ComfyUI/models/loras
  - /home/wjx/ComfyUI/models/lora

示例：
  python3 scripts/add_lora_tips.py                        # 使用内置默认 tips
  python3 scripts/add_lora_tips.py --tips-file tips.txt   # 用外部文件的多行 tips
  python3 scripts/add_lora_tips.py --dirs /path/a /path/b # 自定义扫描目录
  python3 scripts/add_lora_tips.py --dry-run              # 仅查看不写入
"""

from __future__ import annotations

import argparse
import json
import os
from typing import List, Dict, Any


DEFAULT_TIPS: List[str] = [
    "建议强度 0.6~1.0，按风格强弱调节。",
    "提示词中包含触发词后，搭配基础画质短语能更稳定。",
    "若风格过强，可降低 LoRA 强度或增加基础模型权重影响。",
    "与其它 LoRA 同用时，注意总强度相加不宜过高。",
    "建议在正向提示词中靠前位置放置触发词。",
]


def read_lines(file_path: str) -> List[str]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.read().splitlines()]
        return [ln for ln in lines if ln]
    except Exception:
        return []


def normalize_tips(raw: List[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for item in raw:
        if not isinstance(item, str):
            item = str(item)
        for part in str(item).split("\n"):
            tip = part.strip("-• \t").strip()
            if tip and tip not in seen:
                seen.add(tip)
                result.append(tip)
    return result[:20]


def merge_tips_into_meta(meta: Dict[str, Any], new_tips: List[str]) -> bool:
    if not isinstance(meta, dict) or not new_tips:
        return False

    existing_raw: List[str] = []
    for key in ("tips", "usage_tips", "usageTips"):
        val = meta.get(key)
        if isinstance(val, list):
            existing_raw.extend([str(x) for x in val])
        elif isinstance(val, str):
            existing_raw.append(val)

    merged = normalize_tips(existing_raw + new_tips)
    if not merged:
        return False

    meta["tips"] = merged
    return True


def process_meta_file(path: str, new_tips: List[str], dry_run: bool = False) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception as e:
        print(f"[skip] 解析失败: {path} ({e})")
        return False

    # 不修改/覆盖 trainedWords 或 triggerWords，仅合并 tips
    changed = merge_tips_into_meta(meta, new_tips)
    if not changed:
        print(f"[skip] 无需更新: {path}")
        return False

    if dry_run:
        print(f"[dry-run] 将更新 tips: {path}")
        return True

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f"[ok] 更新 tips: {path}")
        return True
    except Exception as e:
        print(f"[fail] 写入失败: {path} ({e})")
        return False


def collect_meta_files(root_dirs: List[str]) -> List[str]:
    result: List[str] = []
    exts = (".json", ".civitai.info")
    for base in root_dirs:
        if not os.path.isdir(base):
            continue
        for dirpath, _, filenames in os.walk(base):
            for fn in filenames:
                if fn.lower().endswith(exts):
                    result.append(os.path.join(dirpath, fn))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="批量为 LoRA 元数据文件添加/合并 tips 字段")
    parser.add_argument(
        "--dirs",
        nargs="*",
        default=[
            "/home/wjx/ComfyUI/models/loras",
            "/home/wjx/ComfyUI/models/lora",
        ],
        help="要扫描的目录列表",
    )
    parser.add_argument("--tips-file", default="", help="外部 tips 文本文件（每行一条）")
    parser.add_argument(
        "--tips",
        default="",
        help="直接在命令行提供的 tips，多个用 '||' 分隔（优先于 --tips-file）",
    )
    parser.add_argument("--dry-run", action="store_true", help="仅预览不写入")
    args = parser.parse_args()

    tips: List[str] = []
    if args.tips:
        tips = [t.strip() for t in args.tips.split("||") if t.strip()]
    elif args.tips_file:
        tips = read_lines(args.tips_file)
    else:
        tips = DEFAULT_TIPS[:]

    tips = normalize_tips(tips)
    files = collect_meta_files(args.dirs)
    print(f"扫描到 {len(files)} 个元数据文件；将写入 {len(tips)} 条 tips。dry_run={args.dry_run}")

    updated = 0
    for p in files:
        if process_meta_file(p, tips, dry_run=args.dry_run):
            updated += 1

    print(f"完成。触达文件: {len(files)}，更新文件: {updated}")


if __name__ == "__main__":
    main()


