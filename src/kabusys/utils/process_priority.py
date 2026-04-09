# src/kabusys/utils/process_priority.py
"""process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ。

Windows と Linux の差分を吸収し、呼び出し元はプラットフォームを意識しない。
"""
from __future__ import annotations

import logging
import platform

import psutil

logger = logging.getLogger(__name__)

_VALID_LEVELS = frozenset({"high", "normal", "low"})

_WINDOWS_PRIORITY = {
    "high":   psutil.HIGH_PRIORITY_CLASS,
    "normal": psutil.NORMAL_PRIORITY_CLASS,
    "low":    psutil.IDLE_PRIORITY_CLASS,
}

_LINUX_NICE = {
    "high":   -10,
    "normal":  0,
    "low":     10,
}


def set_process_priority(level: str) -> None:
    """カレントプロセスの優先度を設定する。

    Args:
        level: "high" | "normal" | "low"

    Raises:
        ValueError: level が無効な場合
    """
    if level not in _VALID_LEVELS:
        raise ValueError(
            f"level が不正です: {level!r}. 有効な値: {sorted(_VALID_LEVELS)}"
        )
    try:
        p = psutil.Process()
        if platform.system() == "Windows":
            p.nice(_WINDOWS_PRIORITY[level])
        else:
            p.nice(_LINUX_NICE[level])
        logger.debug("プロセス優先度を %r に設定しました (PID=%d)", level, p.pid)
    except psutil.AccessDenied:
        logger.warning(
            "プロセス優先度の設定に失敗しました（権限不足）。"
            "管理者権限で実行するか、優先度設定をスキップします。"
        )


def set_cpu_affinity(cpu_count: int | None = None) -> None:
    """カレントプロセスを最初の N コアに固定する。

    Args:
        cpu_count: 使用するコア数。None の場合は設定しない（全コア使用）。
    """
    if cpu_count is None:
        return
    try:
        p = psutil.Process()
        available = list(range(psutil.cpu_count() or 1))
        p.cpu_affinity(available[:cpu_count])
        logger.debug(
            "CPU affinity を %r に設定しました (PID=%d)", available[:cpu_count], p.pid
        )
    except psutil.AccessDenied:
        logger.warning(
            "CPU affinity の設定に失敗しました（権限不足）。スキップします。"
        )
