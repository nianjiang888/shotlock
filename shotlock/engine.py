"""ShotLock 校验引擎。

用法：
    report = validate(load("deck.json"))
    if report.blocked:
        ...不要往下一环节走...
"""

from __future__ import annotations

import json
from typing import Iterable

from .rules import LEVEL_TEXT, P0, P1, P2, RULES, Issue
from .schema import Script

LEVEL_ORDER = {P0: 0, P1: 1, P2: 2}


class Report:
    def __init__(self, script: Script, issues: list[Issue], ran_rules: list[str]):
        self.script = script
        self.issues = sorted(issues, key=lambda x: (LEVEL_ORDER[x.level], x.rule_id, x.shot_id))
        self.ran_rules = ran_rules

    @property
    def counts(self) -> dict[str, int]:
        c = {P0: 0, P1: 0, P2: 0}
        for i in self.issues:
            c[i.level] += 1
        return c

    @property
    def blocked(self) -> bool:
        """有 P0 就阻断。这是唯一会拦截流程的判断。"""
        return any(i.level == P0 for i in self.issues)

    @property
    def verdict(self) -> str:
        if self.blocked:
            return "阻断"
        if self.counts[P1] > 0:
            return "通过（有严重项待修）"
        if self.counts[P2] > 0:
            return "通过（有建议项）"
        return "通过"

    def by_rule(self) -> dict[str, list[Issue]]:
        out: dict[str, list[Issue]] = {}
        for i in self.issues:
            out.setdefault(i.rule_id, []).append(i)
        return out

    def to_dict(self) -> dict:
        return {
            "title": self.script.title,
            "spec_version": "0.1",
            "verdict": self.verdict,
            "blocked": self.blocked,
            "counts": {LEVEL_TEXT[k]: v for k, v in self.counts.items()},
            "total_duration_sec": round(self.script.total_duration, 1),
            "target_duration_sec": round(self.script.target_duration, 1),
            "shot_count": len(self.script.shots),
            "issues": [i.to_dict() for i in self.issues],
        }


def load(path: str) -> Script:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("分镜文件顶层必须是对象")
    return Script.from_dict(data)


def validate(
    script: Script,
    only: Iterable[str] | None = None,
    skip: Iterable[str] | None = None,
    fail_on: str = P0,
) -> Report:
    """跑规则集。only / skip 按规则 ID 过滤，方便分阶段接入。"""
    only_set = set(only) if only else None
    skip_set = set(skip) if skip else set()

    issues: list[Issue] = []
    ran: list[str] = []
    for rule_id, _name, fn in RULES:
        if only_set is not None and rule_id not in only_set:
            continue
        if rule_id in skip_set:
            continue
        ran.append(rule_id)
        try:
            issues.extend(fn(script))
        except Exception as exc:  # 单条规则炸了不能连累整份报告
            issues.append(Issue(rule_id, P1, "-", f"规则执行异常：{exc}", "这是引擎的问题，请提 issue"))
    return Report(script, issues, ran)
