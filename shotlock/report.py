"""报告输出：终端文本版 + 自包含 HTML 版。

HTML 版所有样式内联，不引外部资源，双击能开，Ctrl+P 能存 PDF，
因此可以直接丢进仓库当 Gallery 证据，也可以贴给甲方看。
"""

from __future__ import annotations

from html import escape

from .rules import LEVEL_TEXT, P0, P1, P2, RULE_INDEX
from .engine import Report

_BAR = "=" * 62
_THIN = "-" * 62


def to_text(report: Report) -> str:
    s = report.script
    lines: list[str] = []
    lines.append(_BAR)
    lines.append(f"ShotLock 一致性报告  ·  {s.title or '(未命名)'}")
    lines.append(_BAR)
    lines.append(
        f"镜头 {len(s.shots)} 个 · 角色 {len(s.characters)} 个 · 场景 {len(s.scenes)} 个"
    )
    lines.append(
        f"总时长 {s.total_duration:.1f}s"
        + (f" / 目标 {s.target_duration:.1f}s" if s.target_duration > 0 else "")
    )
    lines.append("")
    lines.append(f"结论：{report.verdict}")
    c = report.counts
    lines.append(f"阻断 {c[P0]} · 严重 {c[P1]} · 建议 {c[P2]}   共 {len(report.issues)} 项")
    lines.append(_THIN)

    if not report.issues:
        lines.append("没有发现问题。")
        lines.append(_BAR)
        return "\n".join(lines)

    grouped = report.by_rule()
    for rule_id in sorted(grouped):
        items = grouped[rule_id]
        name = RULE_INDEX.get(rule_id, "")
        lines.append("")
        lines.append(f"[{items[0].level}] {rule_id} {name}  ({len(items)})")
        for it in items:
            lines.append(f"    镜头 {it.shot_id}：{it.message}")
            if it.hint:
                lines.append(f"              → {it.hint}")
    lines.append("")
    lines.append(_BAR)
    return "\n".join(lines)


def to_html(report: Report) -> str:
    s = report.script
    c = report.counts
    grouped = report.by_rule()

    def badge(level: str) -> str:
        color = {P0: "#A32D2D", P1: "#854F0B", P2: "#185FA5"}[level]
        bg = {P0: "#FCEBEB", P1: "#FAEEDA", P2: "#E6F1FB"}[level]
        return (
            f'<span style="display:inline-block;padding:1px 8px;border-radius:4px;'
            f'font-size:12px;color:{color};background:{bg}">{level} {LEVEL_TEXT[level]}</span>'
        )

    rows: list[str] = []
    for rule_id in sorted(grouped):
        items = grouped[rule_id]
        name = RULE_INDEX.get(rule_id, "")
        cells: list[str] = []
        for it in items:
            hint = f'<div style="margin-top:4px;color:#5F5E5A;font-size:12px">→ {escape(it.hint)}</div>' if it.hint else ""
            cells.append(
                f'<tr><td style="padding:8px 10px;border-bottom:1px solid #EEEEEE;'
                f'vertical-align:top;white-space:nowrap;font-family:Consolas,monospace;font-size:12px">'
                f'{escape(it.shot_id)}</td>'
                f'<td style="padding:8px 10px;border-bottom:1px solid #EEEEEE">'
                f'{escape(it.message)}{hint}</td></tr>'
            )
        rows.append(
            f'<div style="margin:18px 0 0">'
            f'<div style="font-size:14px;font-weight:500;margin-bottom:6px">'
            f'{badge(items[0].level)} &nbsp;{escape(rule_id)} {escape(name)} '
            f'<span style="color:#888780;font-size:12px">({len(items)})</span></div>'
            f'<table style="width:100%;border-collapse:collapse;font-size:13px">{ "".join(cells) }</table>'
            f"</div>"
        )

    body = (
        "".join(rows)
        if rows
        else '<div style="padding:16px;background:#EAF3DE;border-radius:8px;color:#3B6D11">没有发现问题。</div>'
    )

    verdict_color = "#A32D2D" if report.blocked else ("#854F0B" if c[P1] else "#3B6D11")

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ShotLock 报告 · {escape(s.title or "未命名")}</title></head>
<body style="margin:0;padding:32px;background:#F7F7F5;color:#2C2C2A;
font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;line-height:1.6">
<div style="max-width:860px;margin:0 auto;background:#FFFFFF;border:1px solid #E5E5E2;border-radius:12px;padding:28px">
<div style="font-size:13px;color:#888780;letter-spacing:.05em">SHOTLOCK CONSISTENCY REPORT</div>
<h1 style="font-size:20px;font-weight:500;margin:6px 0 16px">{escape(s.title or "未命名分镜")}</h1>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:4px">
<tr>
<td style="padding:6px 0;color:#5F5E5A">镜头 / 角色 / 场景</td>
<td style="padding:6px 0">{len(s.shots)} / {len(s.characters)} / {len(s.scenes)}</td>
</tr>
<tr>
<td style="padding:6px 0;color:#5F5E5A">总时长 / 目标</td>
<td style="padding:6px 0">{s.total_duration:.1f}s{f" / {s.target_duration:.1f}s" if s.target_duration > 0 else ""}</td>
</tr>
<tr>
<td style="padding:6px 0;color:#5F5E5A">结论</td>
<td style="padding:6px 0;font-weight:500;color:{verdict_color}">{escape(report.verdict)}</td>
</tr>
<tr>
<td style="padding:6px 0;color:#5F5E5A">问题分布</td>
<td style="padding:6px 0">阻断 {c[P0]} · 严重 {c[P1]} · 建议 {c[P2]}</td>
</tr>
</table>
<hr style="border:none;border-top:1px solid #EEEEEE;margin:20px 0">
{body}
<div style="margin-top:24px;padding-top:14px;border-top:1px solid #EEEEEE;color:#888780;font-size:12px">
ShotLock · 分镜脚本结构化规范与一致性校验引擎 · ShotSpec v0.1
</div>
</div></body></html>"""
