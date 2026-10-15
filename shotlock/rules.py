"""ShotLock 一致性规则集。

每条规则是一个函数，接收 Script，返回 Issue 列表。规则分三级：
    P0 阻断  —— 数据结构或物理上不成立，不修没法往下一环节走
    P1 严重  —— 发布前必修，观众能看出来
    P2 建议  —— 影响观感，视风格取舍

规则 ID 稳定不变，方便在 CI 或 Agent 工作流里按 ID 屏蔽或强制。
"""

from __future__ import annotations

import re
from typing import Callable

from .schema import (
    CAMERA_MOVES,
    DURATION_BUDGET_TOLERANCE,
    EMOTIONS,
    ESTABLISHING_SIZES,
    INT_EXT,
    MAX_SHOT_DURATION,
    MAX_SPEECH_RATE,
    MAX_SUBTITLE_CHARS,
    MIN_SHOT_DURATION,
    MIN_SPEECH_RATE,
    SCREEN_DIR,
    SHOT_SIZES,
    TRANSITIONS,
    Script,
    Shot,
)

P0, P1, P2 = "P0", "P1", "P2"

LEVEL_TEXT = {
    P0: "阻断",
    P1: "严重",
    P2: "建议",
}


class Issue:
    __slots__ = ("rule_id", "level", "shot_id", "message", "hint")

    def __init__(self, rule_id: str, level: str, shot_id: str, message: str, hint: str = ""):
        self.rule_id = rule_id
        self.level = level
        self.shot_id = shot_id
        self.message = message
        self.hint = hint

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "level": self.level,
            "shot_id": self.shot_id,
            "message": self.message,
            "hint": self.hint,
        }


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

_CJK = re.compile(r"[\u4e00-\u9fff]")
_LATIN_WORD = re.compile(r"[A-Za-z]+")


def count_speakable(text: str) -> int:
    """估算念完这段台词需要多少"字"。中文按字计，英文按词计。"""
    if not text:
        return 0
    cjk = len(_CJK.findall(text))
    latin = len(_LATIN_WORD.findall(text))
    return cjk + latin


def visible_len(text: str) -> int:
    """字幕占位宽度。中文按 1 计，英文按半个字宽估算。"""
    if not text:
        return 0
    cjk = len(_CJK.findall(text))
    others = len([c for c in text if c.strip() and not _CJK.match(c)])
    return cjk + others / 2


# 外貌属性维度：同一维度出现互斥取值即为漂移。
# 这是 AI 生成长剧本时最常见的崩法——第二十场角色发色突然变了。
APPEARANCE_DIMENSIONS: dict[str, dict[str, tuple[str, ...]]] = {
    "发长": {
        "长发": ("长发", "及肩", "披肩", "过肩"),
        "短发": ("短发", "齐耳", "寸头", "板寸"),
        "束发": ("马尾", "盘发", "丸子头", "扎起"),
    },
    "发色": {
        "黑色": ("黑发", "乌黑", "黑色头发", "黑长直"),
        "棕色": ("棕发", "栗色", "咖啡色头发"),
        "金色": ("金发", "金色头发", "亚麻色"),
        "白色": ("白发", "银发", "花白"),
    },
    "服装色": {
        "深色": ("黑衣", "黑色外套", "深色西装", "藏青", "墨绿"),
        "浅色": ("白衣", "米色", "浅色", "杏色", "奶白"),
        "红色": ("红衣", "红色连衣裙", "酒红"),
        "蓝色": ("蓝衣", "牛仔", "藏蓝", "天蓝"),
    },
    "年龄感": {
        "青年": ("二十", "青年", "年轻", "大学生"),
        "中年": ("四十", "中年", "五十", "成熟"),
        "老年": ("老年", "白发苍苍", "七十", "八十", "拄拐"),
    },
}


def _dim_value(text: str, dim: str) -> str | None:
    """从一段描述里提取某维度的取值。命中多个取第一个。"""
    for value, keywords in APPEARANCE_DIMENSIONS[dim].items():
        for kw in keywords:
            if kw in text:
                return value
    return None


def _character_appearance_text(c) -> str:
    return " ".join(str(v) for v in c.appearance.values() if v)


# ---------------------------------------------------------------------------
# P0 规则
# ---------------------------------------------------------------------------


def rule_schema(script: Script) -> list[Issue]:
    """SL001 结构完整性：必需字段、枚举取值、正负数值。"""
    issues: list[Issue] = []

    if not script.shots:
        issues.append(Issue("SL001", P0, "-", "分镜序列为空，没有任何镜头", "至少需要一个镜头"))
        return issues

    if not script.characters:
        issues.append(Issue("SL001", P2, "-", "角色表为空，镜头里若有角色将无法校验一致性", ""))

    seen_shot_ids: set[str] = set()
    for shot in script.shots:
        sid = shot.id or "(无 id)"

        if not shot.id:
            issues.append(Issue("SL001", P0, sid, "镜头缺少 id", "id 是跨环节引用的主键"))
        elif shot.id in seen_shot_ids:
            issues.append(Issue("SL001", P0, sid, f"镜头 id 重复：{shot.id}", "重复 id 会让 downstream 覆盖"))
        seen_shot_ids.add(shot.id)

        if not shot.scene_id:
            issues.append(Issue("SL001", P0, sid, "镜头未指定 scene_id", ""))

        if shot.shot_size and shot.shot_size not in SHOT_SIZES:
            issues.append(
                Issue("SL001", P0, sid, f"景别取值非法：{shot.shot_size}", f"合法值：{', '.join(SHOT_SIZES)}")
            )
        if shot.camera_move and shot.camera_move not in CAMERA_MOVES:
            issues.append(
                Issue("SL001", P0, sid, f"运镜取值非法：{shot.camera_move}", f"合法值：{', '.join(CAMERA_MOVES)}")
            )
        if shot.transition_in and shot.transition_in not in TRANSITIONS:
            issues.append(
                Issue("SL001", P0, sid, f"转场取值非法：{shot.transition_in}", f"合法值：{', '.join(TRANSITIONS)}")
            )
        if shot.emotion and shot.emotion not in EMOTIONS:
            issues.append(Issue("SL001", P2, sid, f"情绪标签未收录：{shot.emotion}", f"已收录：{', '.join(EMOTIONS)}"))

        if shot.duration_sec <= 0:
            issues.append(Issue("SL001", P0, sid, "时长缺失或不大于 0", "duration_sec 必须为正数"))

        for sc in shot.characters:
            if sc.screen_dir not in SCREEN_DIR:
                issues.append(
                    Issue("SL001", P1, sid, f"角色 {sc.id} 的 screen_dir 取值非法：{sc.screen_dir}",
                          f"合法值：{', '.join(SCREEN_DIR)}")
                )
        for line in shot.dialogue:
            if not line.speaker:
                issues.append(Issue("SL001", P0, sid, "台词缺少 speaker", ""))

    for s in script.scenes:
        if s.int_ext and s.int_ext not in INT_EXT:
            issues.append(Issue("SL001", P1, "-", f"场景 {s.id} 的 int_ext 取值非法：{s.int_ext}",
                                f"合法值：{', '.join(INT_EXT)}"))

    char_ids = {c.id for c in script.characters}
    if len(char_ids) != len(script.characters):
        issues.append(Issue("SL001", P0, "-", "角色表存在重复 id", ""))

    scene_ids = {s.id for s in script.scenes}
    if len(scene_ids) != len(script.scenes):
        issues.append(Issue("SL001", P0, "-", "场景表存在重复 id", ""))

    return issues


def rule_shot_duration(script: Script) -> list[Issue]:
    """SL002 单镜头时长边界。太短剪不出来，太长短剧节奏会垮。"""
    issues: list[Issue] = []
    for shot in script.shots:
        if shot.duration_sec <= 0:
            continue
        if shot.duration_sec < MIN_SHOT_DURATION:
            issues.append(
                Issue("SL002", P0, shot.id,
                      f"镜头时长 {shot.duration_sec:.1f}s 低于下限 {MIN_SHOT_DURATION}s，实际不可剪",
                      "合并到相邻镜头，或延长到 1.5s 以上")
            )
        elif shot.duration_sec > MAX_SHOT_DURATION:
            issues.append(
                Issue("SL002", P1, shot.id,
                      f"镜头时长 {shot.duration_sec:.1f}s 超过上限 {MAX_SHOT_DURATION}s",
                      "拆成两个镜头，中间插 reaction 或 insert")
            )
    return issues


def rule_speech_rate(script: Script) -> list[Issue]:
    """SL003 台词语速。配音念不完是短剧最常翻车的地方，因为生成剧本时没人算这个。"""
    issues: list[Issue] = []
    for shot in script.shots:
        if shot.duration_sec <= 0:
            continue
        for line in shot.dialogue:
            n = count_speakable(line.text)
            if n == 0:
                continue
            rate = n / shot.duration_sec
            if rate > MAX_SPEECH_RATE:
                need_sec = n / MAX_SPEECH_RATE
                max_chars = int(shot.duration_sec * MAX_SPEECH_RATE)
                issues.append(
                    Issue("SL003", P0, shot.id,
                          f"台词 {n} 字 / {shot.duration_sec:.1f}s = {rate:.1f} 字每秒，超过上限 {MAX_SPEECH_RATE}，配音念不完",
                          f"砍到 {max_chars} 字以内，或把镜头延长到 {need_sec:.1f}s")
                )
            elif rate < MIN_SPEECH_RATE:
                min_chars = int(shot.duration_sec * MIN_SPEECH_RATE) + 1
                issues.append(
                    Issue("SL003", P2, shot.id,
                          f"台词 {n} 字 / {shot.duration_sec:.1f}s = {rate:.1f} 字每秒，低于 {MIN_SPEECH_RATE}，听着拖",
                          f"加到 {min_chars} 字以上，或把镜头压到 {n / MIN_SPEECH_RATE:.1f}s")
                )
    return issues


def rule_character_registered(script: Script) -> list[Issue]:
    """SL006 镜头里的角色必须在角色表注册过。"""
    known = {c.id for c in script.characters}
    issues: list[Issue] = []
    for shot in script.shots:
        for sc in shot.characters:
            if sc.id and sc.id not in known:
                issues.append(
                    Issue("SL006", P0, shot.id,
                          f"镜头引用了未注册角色：{sc.id}",
                          "在 characters 里补上该角色的外貌定义，出图才能保持一致性")
                )
        for line in shot.dialogue:
            if line.speaker and line.speaker not in known and line.speaker not in ("旁白", "OS", "VO"):
                issues.append(Issue("SL006", P1, shot.id, f"台词说话人未注册：{line.speaker}", ""))
    return issues


def rule_scene_registered(script: Script) -> list[Issue]:
    """SL007 镜头引用的场景必须在场景表存在。"""
    known = {s.id for s in script.scenes}
    issues: list[Issue] = []
    if not script.scenes:
        return issues
    for shot in script.shots:
        if shot.scene_id and shot.scene_id not in known:
            issues.append(Issue("SL007", P0, shot.id, f"镜头引用了未注册场景：{shot.scene_id}", ""))
    return issues


# ---------------------------------------------------------------------------
# P1 规则
# ---------------------------------------------------------------------------


def rule_appearance_drift(script: Script) -> list[Issue]:
    """SL004 角色外貌漂移：镜头内的临时描述与角色表定义互斥。"""
    issues: list[Issue] = []
    for shot in script.shots:
        for sc in shot.characters:
            base = script.character_by_id(sc.id)
            if base is None or not sc.appearance_note:
                continue
            base_text = _character_appearance_text(base)
            if not base_text:
                continue
            for dim in APPEARANCE_DIMENSIONS:
                v_base = _dim_value(base_text, dim)
                v_shot = _dim_value(sc.appearance_note, dim)
                if v_base and v_shot and v_base != v_shot:
                    issues.append(
                        Issue("SL004", P1, shot.id,
                              f"角色 {base.name or sc.id} 的{dim}漂移：角色表是「{v_base}」，本镜头写成了「{v_shot}」",
                              "出图会串脸。要么改本镜头描述，要么改角色表并同步全剧")
                    )
    return issues


def rule_scene_continuity(script: Script) -> list[Issue]:
    """SL005 场景连续性：同一场景内的时间与光线 override 不得自相矛盾。"""
    issues: list[Issue] = []
    overrides: dict[str, dict[str, set[str]]] = {}
    for shot in script.shots:
        raw = getattr(shot, "continuity_override", None) or {}
        for key, label in (("time_of_day", "时间"), ("lighting", "光线")):
            val = raw.get(key)
            if not val:
                continue
            scene = script.scene_by_id(shot.scene_id)
            base_val = getattr(scene, key, "") if scene else ""
            if base_val and val != base_val:
                issues.append(
                    Issue("SL005", P1, shot.id,
                          f"场景 {shot.scene_id} 的{label}被改成「{val}」，与场景表定义的「{base_val}」冲突",
                          "如果是时间流逝，请拆成新场景")
                )
            bucket = overrides.setdefault(shot.scene_id, {}).setdefault(key, set())
            if val not in bucket:
                if bucket:
                    issues.append(
                        Issue("SL005", P1, shot.id,
                              f"场景 {shot.scene_id} 内{label}在中途跳变：{sorted(bucket | {val})}",
                              "同一场景内无过渡地换时间/光线，观众会出戏")
                    )
                bucket.add(val)
    return issues


def rule_axis_crossing(script: Script) -> list[Issue]:
    """SL008 越轴：同一场景相邻镜头里，双人相对画面位置整体对调。

    全景镜头会重设轴线，所以前一个是全景时不算越轴。这是短剧 AI 分镜最难自检的一条，
    因为模型只看单镜头文本，不会记得上一个镜头谁在左边。
    """
    issues: list[Issue] = []
    shots = script.shots
    for i in range(1, len(shots)):
        prev, cur = shots[i - 1], shots[i]
        if not prev.scene_id or prev.scene_id != cur.scene_id:
            continue
        if prev.shot_size in ("EXTREME_WIDE", "WIDE"):
            continue

        prev_dirs = {c.id: c.screen_dir for c in prev.characters if c.screen_dir in ("left", "right")}
        cur_dirs = {c.id: c.screen_dir for c in cur.characters if c.screen_dir in ("left", "right")}
        common = set(prev_dirs) & set(cur_dirs)
        if len(common) < 2:
            continue

        flipped = [cid for cid in common if prev_dirs[cid] != cur_dirs[cid]]
        if len(flipped) == len(common):
            names = []
            for cid in sorted(common):
                c = script.character_by_id(cid)
                names.append(c.name if c and c.name else cid)
            issues.append(
                Issue("SL008", P1, cur.id,
                      f"疑似越轴：{', '.join(names)} 的画面左右位置在镜头 {prev.id} → {cur.id} 之间整体对调",
                      "插一个全景或骑轴镜头重设轴线，或把本镜头的 screen_dir 改回上一镜的配置")
            )
    return issues


def rule_duration_budget(script: Script) -> list[Issue]:
    """SL009 集总时长预算。"""
    issues: list[Issue] = []
    target = script.target_duration
    if target <= 0:
        return issues
    total = script.total_duration
    deviation = abs(total - target) / target
    if deviation > DURATION_BUDGET_TOLERANCE:
        diff = total - target
        direction = "超出" if diff > 0 else "不足"
        issues.append(
            Issue("SL009", P1, "-",
                  f"总时长 {total:.1f}s，目标 {target:.1f}s，{direction} {abs(diff):.1f}s（偏差 {deviation * 100:.0f}%）",
                  f"把偏差压到 {DURATION_BUDGET_TOLERANCE * 100:.0f}% 以内，平台分集时长是按这个切的")
        )
    return issues


def rule_transition_abuse(script: Script) -> list[Issue]:
    """SL010 转场滥用：连续叠化、集首集尾的进出方式。"""
    issues: list[Issue] = []
    shots = script.shots
    if not shots:
        return issues

    first = shots[0]
    if first.transition_in in ("DISSOLVE", "WIPE", "IRIS"):
        issues.append(
            Issue("SL010", P2, first.id,
                  f"开场用了 {first.transition_in}，短剧开场一般用硬开或淡入",
                  "改成 FADE_IN 或 CUT")
        )

    streak = 0
    for i, shot in enumerate(shots):
        if shot.transition_in == "DISSOLVE":
            streak += 1
            if streak >= 3:
                issues.append(
                    Issue("SL010", P1, shot.id,
                          f"连续第 {streak} 个叠化转场，节奏会被拖垮",
                          "叠化只用于时间跳跃，对话段落用 CUT")
                )
        else:
            streak = 0

    for shot in shots[:-1]:
        if shot.transition_in == "FADE_OUT":
            issues.append(Issue("SL010", P1, shot.id, "非末尾镜头出现 FADE_OUT，会把剧切断", "改为 CUT 或 DISSOLVE"))
    if shots and shots[-1].transition_in not in ("FADE_OUT", "FADE_IN", "CUT"):
        issues.append(Issue("SL010", P2, shots[-1].id, "集尾缺少收尾转场", "最后一个镜头用 FADE_OUT"))
    return issues


def rule_shot_size_rhythm(script: Script) -> list[Issue]:
    """SL011 景别节奏：长镜头堆同一景别会让画面发闷。"""
    issues: list[Issue] = []
    shots = script.shots
    run_start = 0
    for i in range(1, len(shots) + 1):
        same = i < len(shots) and shots[i].shot_size == shots[run_start].shot_size
        if same:
            continue
        run = shots[run_start:i]
        size = run[0].shot_size if run else ""
        if size and size != "INSERT" and len(run) >= 4:
            avg = sum(s.duration_sec for s in run) / len(run)
            level = P1 if avg > 3.5 else P2
            ids = f"{run[0].id}~{run[-1].id}"
            issues.append(
                Issue("SL011", level, ids,
                      f"连续 {len(run)} 个 {size}，平均单镜 {avg:.1f}s",
                      "中间插入反打、insert 或换景别，打破视觉惯性")
            )
        run_start = i
    return issues


# ---------------------------------------------------------------------------
# P2 规则
# ---------------------------------------------------------------------------


def rule_emotion_monotony(script: Script) -> list[Issue]:
    """SL012 情绪单调：连续四个以上同情绪镜头，观众会觉得没推进。"""
    issues: list[Issue] = []
    shots = script.shots
    run_start = 0
    for i in range(1, len(shots) + 1):
        same = i < len(shots) and shots[i].emotion == shots[run_start].emotion
        if same:
            continue
        run = shots[run_start:i]
        emo = run[0].emotion if run else ""
        if emo and emo != "neutral" and len(run) >= 4:
            issues.append(
                Issue("SL012", P2, f"{run[0].id}~{run[-1].id}",
                      f"连续 {len(run)} 个镜头情绪都是 {emo}",
                      "给其中一两个镜头换情绪，或加一个 reaction 镜头")
            )
        run_start = i
    return issues


def rule_subtitle_length(script: Script) -> list[Issue]:
    """SL013 字幕过长：竖屏一行放不下会折行遮挡画面。"""
    issues: list[Issue] = []
    for shot in script.shots:
        for line in shot.dialogue:
            n = visible_len(line.subtitle or line.text)
            if n > MAX_SUBTITLE_CHARS:
                issues.append(
                    Issue("SL013", P2, shot.id,
                          f"字幕约 {n:.0f} 字宽，超过建议上限 {MAX_SUBTITLE_CHARS}",
                          "拆成两条字幕分到两个镜头，或精简文案")
                )
    return issues


def rule_prop_flicker(script: Script) -> list[Issue]:
    """SL014 物件闪现：同一场景内某角色手上的东西消失又出现。"""
    issues: list[Issue] = []
    by_scene: dict[str, list[Shot]] = {}
    for shot in script.shots:
        by_scene.setdefault(shot.scene_id, []).append(shot)

    for scene_id, shots in by_scene.items():
        tracks: dict[str, list[tuple[str, str]]] = {}
        for shot in shots:
            for sc in shot.characters:
                tracks.setdefault(sc.id, []).append((shot.id, sc.holding or ""))
        for cid, seq in tracks.items():
            for i in range(1, len(seq) - 1):
                prev_id, prev_val = seq[i - 1]
                cur_id, cur_val = seq[i]
                next_id, next_val = seq[i + 1]
                if prev_val and not cur_val and next_val and prev_val == next_val:
                    name = script.character_by_id(cid)
                    issues.append(
                        Issue("SL014", P2, cur_id,
                              f"角色 {name.name if name else cid} 的「{prev_val}」在 {cur_id} 消失、{next_id} 又出现",
                              "要么保留到底，要么加一个放下/拿起的动作镜头")
                    )
    return issues


def rule_establishing_shot(script: Script) -> list[Issue]:
    """SL015 缺少建置镜头：场景首次出现没有给全景，观众不知道在哪。"""
    issues: list[Issue] = []
    seen: set[str] = set()
    for shot in script.shots:
        if shot.scene_id in seen:
            continue
        seen.add(shot.scene_id)
        if shot.shot_size and shot.shot_size not in ESTABLISHING_SIZES:
            scene = script.scene_by_id(shot.scene_id)
            loc = scene.location if scene else shot.scene_id
            issues.append(
                Issue("SL015", P2, shot.id,
                      f"场景「{loc}」首次出现用了 {shot.shot_size}，没有建置镜头",
                      "短剧可以省，但换个场景时给一个 WIDE 更稳")
            )
    return issues


RULES: list[tuple[str, str, Callable[[Script], list[Issue]]]] = [
    ("SL001", "结构完整性", rule_schema),
    ("SL002", "镜头时长边界", rule_shot_duration),
    ("SL003", "台词语速", rule_speech_rate),
    ("SL006", "角色注册", rule_character_registered),
    ("SL007", "场景注册", rule_scene_registered),
    ("SL004", "角色外貌漂移", rule_appearance_drift),
    ("SL005", "场景连续性", rule_scene_continuity),
    ("SL008", "越轴检测", rule_axis_crossing),
    ("SL009", "总时长预算", rule_duration_budget),
    ("SL010", "转场合法性", rule_transition_abuse),
    ("SL011", "景别节奏", rule_shot_size_rhythm),
    ("SL012", "情绪单调", rule_emotion_monotony),
    ("SL013", "字幕长度", rule_subtitle_length),
    ("SL014", "物件闪现", rule_prop_flicker),
    ("SL015", "建置镜头", rule_establishing_shot),
]

RULE_INDEX = {rid: name for rid, name, _ in RULES}
