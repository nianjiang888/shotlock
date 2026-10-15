"""命令行入口：python -m shotlock deck.json

退出码沿用引擎约定：0 通过 / 1 存在达到拦截级别的问题 / 2 输入错误 / 3 内部错误。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from .engine import load, validate
from .report import to_html, to_text
from .rules import P0, P1, P2


def _utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except Exception:
            pass


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="shotlock",
        description="校验短剧分镜脚本的一致性",
    )
    p.add_argument("input", help="分镜 JSON 文件路径")
    p.add_argument("--json", dest="json_out", help="把结构化结果写到指定文件")
    p.add_argument("--html", dest="html_out", help="把 HTML 报告写到指定文件")
    p.add_argument("--only", help="只跑指定规则，逗号分隔，如 SL003,SL008")
    p.add_argument("--skip", help="跳过指定规则，逗号分隔")
    p.add_argument(
        "--fail-on",
        choices=[P0, P1, P2],
        default=P0,
        help="达到该级别就返回非零退出码，默认 P0",
    )
    p.add_argument("--quiet", action="store_true", help="只打印结论行")
    return p


def main(argv: list[str] | None = None) -> int:
    _utf8()
    args = build_parser().parse_args(argv)

    try:
        script = load(args.input)
    except FileNotFoundError:
        print(f"输入错误：找不到文件 {args.input}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"输入错误：{exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"内部错误：{exc}", file=sys.stderr)
        return 3

    try:
        split = lambda s: [x.strip() for x in s.split(",") if x.strip()] if s else None
        report = validate(script, only=split(args.only), skip=split(args.skip))
    except Exception as exc:
        print(f"内部错误：{exc}", file=sys.stderr)
        return 3

    if not args.quiet:
        print(to_text(report))

    def _write(path: str, text: str, label: str) -> None:
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"已写出 {label}：{path}")

    if args.json_out:
        _write(args.json_out, json.dumps(report.to_dict(), ensure_ascii=False, indent=2), "JSON 结果")

    if args.html_out:
        _write(args.html_out, to_html(report), "HTML 报告")

    levels = {P0: 0, P1: 1, P2: 2}
    threshold = levels[args.fail_on]
    hit = any(levels[i.level] <= threshold for i in report.issues)
    return 1 if hit else 0


if __name__ == "__main__":
    raise SystemExit(main())
