"""ShotLock — 短剧分镜脚本的结构化规范与一致性校验引擎。"""

from .engine import Report, load, validate
from .rules import RULES, RULE_INDEX
from .report import to_html, to_text
from .schema import Script

__version__ = "0.1.0"
__all__ = ["Script", "Report", "load", "validate", "to_text", "to_html", "RULES", "RULE_INDEX"]
