"""ShotLock 分镜脚本规范（ShotSpec v0.1）

一个分镜脚本由四层组成：meta（集元信息）、characters（角色表）、scenes（场景表）、shots（镜头序列）。
shots 里的每个镜头通过 id 引用 characters 和 scenes，不允许内联重复定义实体。

设计取舍：
- 用 screen_dir 显式声明角色在画面中的左右位置，越轴检测才有依据。靠自然语言描述推断左右不可靠。
- 时长单位统一用秒（浮点），不用帧，因为短剧素材多来自不同生成管线，帧率不一定统一。
- 枚举用大写下划线，方便 LLM 稳定输出，也方便校验时直接比对。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SHOT_SPEC_VERSION = "0.1"

# 景别。短剧竖屏场景下 WIDE 已经算远景，EXTREME_WIDE 主要用于空镜和建置
SHOT_SIZES = (
    "EXTREME_WIDE",  # 大远景，环境为主
    "WIDE",          # 全景，人物全身带环境
    "FULL",          # 全身，人物为主
    "MEDIUM",        # 中景，腰部以上
    "CLOSE_UP",      # 特写，肩部以上
    "EXTREME_CLOSE_UP",  # 大特写，眼睛/手/物件
    "INSERT",        # 插入镜头，物件或细节
    "OTS",           # 过肩
    "TWO_SHOT",      # 双人同框
    "POV",           # 主观视角
)

# 运镜
CAMERA_MOVES = (
    "STATIC", "PAN", "TILT", "DOLLY", "TRACK",
    "CRANE", "HANDHELD", "ZOOM", "FOLLOW", "ORBIT",
)

# 入点转场
TRANSITIONS = (
    "CUT", "FADE_IN", "FADE_OUT", "DISSOLVE",
    "WIPE", "MATCH_CUT", "JUMP_CUT", "IRIS",
)

# 内外景
INT_EXT = ("INT", "EXT", "INT_EXT")

# 画面位置，越轴检测的核心字段
SCREEN_DIR = ("left", "center", "right", "offscreen")

# 情绪标签，用于检测情绪单调
EMOTIONS = (
    "neutral", "calm", "tense", "angry", "sad",
    "joy", "fear", "surprised", "disgusted", "affectionate",
)

# 单镜头时长边界（秒）。低于下限剪不出来，高于上限短剧节奏会垮
MIN_SHOT_DURATION = 1.5
MAX_SHOT_DURATION = 25.0

# 中文对白语速（字/秒）。
# 上限 7.5：配音演员在带情绪时很难稳定超过这个速度，超了必然吞字。
# 下限 2.2：再慢就真的拖了。设成 3.0 会误伤短句——一句五个字配两秒镜头是完全正常的表演节奏。
MIN_SPEECH_RATE = 2.2
MAX_SPEECH_RATE = 7.5

# 单条字幕建议上限（中文字符）
MAX_SUBTITLE_CHARS = 18

# 集总时长允许的偏差比例
DURATION_BUDGET_TOLERANCE = 0.15

# 建置镜头：一个场景的第一个镜头应该是这些景别之一
ESTABLISHING_SIZES = ("EXTREME_WIDE", "WIDE", "FULL")


@dataclass
class Character:
    id: str
    name: str
    appearance: dict[str, str] = field(default_factory=dict)
    traits: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Character":
        return cls(
            id=str(d.get("id", "")),
            name=str(d.get("name", "")),
            appearance=dict(d.get("appearance") or {}),
            traits=list(d.get("traits") or []),
        )


@dataclass
class Scene:
    id: str
    location: str = ""
    time_of_day: str = ""
    lighting: str = ""
    int_ext: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Scene":
        return cls(
            id=str(d.get("id", "")),
            location=str(d.get("location", "")),
            time_of_day=str(d.get("time_of_day", "")),
            lighting=str(d.get("lighting", "")),
            int_ext=str(d.get("int_ext", "")),
        )


@dataclass
class ShotCharacter:
    id: str
    screen_dir: str = "center"
    appearance_note: str = ""
    holding: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ShotCharacter":
        return cls(
            id=str(d.get("id", "")),
            screen_dir=str(d.get("screen_dir", "center")),
            appearance_note=str(d.get("appearance_note", "")),
            holding=str(d.get("holding", "")),
        )


@dataclass
class DialogueLine:
    speaker: str
    text: str
    subtitle: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DialogueLine":
        return cls(
            speaker=str(d.get("speaker", "")),
            text=str(d.get("text", "")),
            subtitle=str(d.get("subtitle", "") or d.get("text", "")),
        )


@dataclass
class Shot:
    id: str
    scene_id: str = ""
    duration_sec: float = 0.0
    shot_size: str = ""
    camera_move: str = ""
    transition_in: str = "CUT"
    characters: list[ShotCharacter] = field(default_factory=list)
    dialogue: list[DialogueLine] = field(default_factory=list)
    emotion: str = "neutral"
    action: str = ""
    props: list[str] = field(default_factory=list)
    notes: str = ""
    # 仅当本镜头的时间或光线确实偏离场景表定义时才填，比如一场戏从黄昏演到深夜。
    # 填了就会触发 SL005 连续性校验，别用这个字段掩盖生成时的漂移。
    continuity_override: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Shot":
        return cls(
            id=str(d.get("id", "")),
            scene_id=str(d.get("scene_id", "")),
            duration_sec=_as_float(d.get("duration_sec")),
            shot_size=str(d.get("shot_size", "")),
            camera_move=str(d.get("camera_move", "")),
            transition_in=str(d.get("transition_in", "CUT")),
            characters=[ShotCharacter.from_dict(x) for x in (d.get("characters") or [])],
            dialogue=[DialogueLine.from_dict(x) for x in (d.get("dialogue") or [])],
            emotion=str(d.get("emotion", "neutral")),
            action=str(d.get("action", "")),
            props=list(d.get("props") or []),
            notes=str(d.get("notes", "")),
            continuity_override=dict(d.get("continuity_override") or {}),
        )


@dataclass
class Script:
    """一份完整的分镜脚本。"""

    meta: dict[str, Any] = field(default_factory=dict)
    characters: list[Character] = field(default_factory=list)
    scenes: list[Scene] = field(default_factory=list)
    shots: list[Shot] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Script":
        return cls(
            meta=dict(d.get("meta") or {}),
            characters=[Character.from_dict(x) for x in (d.get("characters") or [])],
            scenes=[Scene.from_dict(x) for x in (d.get("scenes") or [])],
            shots=[Shot.from_dict(x) for x in (d.get("shots") or [])],
        )

    @property
    def title(self) -> str:
        return str(self.meta.get("title", ""))

    @property
    def target_duration(self) -> float:
        return _as_float(self.meta.get("target_duration_sec"))

    @property
    def total_duration(self) -> float:
        return sum(s.duration_sec for s in self.shots)

    def character_by_id(self, cid: str) -> Character | None:
        for c in self.characters:
            if c.id == cid:
                return c
        return None

    def scene_by_id(self, sid: str) -> Scene | None:
        for s in self.scenes:
            if s.id == sid:
                return s
        return None


def _as_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0
