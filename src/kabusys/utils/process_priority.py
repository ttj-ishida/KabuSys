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

# psutil の HIGH_PRIORITY_CLASS 等は Windows 専用定数（Linux では存在しない）
# getattr でフォールバック値を使い、全 OS でモジュールロードを成功させる
_WINDOWS_PRIORITY: dict[str, int] = {
    "high": getattr(psutil, "HIGH_PRIORITY_CLASS", 128),
    "normal": getattr(psutil, "NORMAL_PRIORITY_CLASS", 32),
    "low": getattr(psutil, "IDLE_PRIORITY_CLASS", 64),
}

# POSIX 系 OS の nice 値
_LINUX_NICE = {
    "high": -10,
    "normal": 0,
    "low": 10,
}

# nice() が使える POSIX 系 OS
_SUPPORTED_POSIX = frozenset({"Linux", "Darwin", "FreeBSD"})


def set_process_priority(level: str) -> None:
    """カレントプロセスの優先度を設定する。

    Args:
        level: "high" | "normal" | "low"

    Raises:
        ValueError: level が無効な場合
    """
    if level not in _VALID_LEVELS:
        raise ValueError(f"level が不正です: {level!r}. 有効な値: {sorted(_VALID_LEVELS)}")
    try:
        p = psutil.Process()
        sysname = platform.system()
        if sysname == "Windows":
            p.nice(_WINDOWS_PRIORITY[level])
        elif sysname in _SUPPORTED_POSIX:
            p.nice(_LINUX_NICE[level])
        else:
            logger.warning("未対応 OS (%s) のため優先度設定をスキップします。", sysname)
            return
        logger.debug("プロセス優先度を %r に設定しました (PID=%d)", level, p.pid)
    except (psutil.AccessDenied, AttributeError, NotImplementedError) as e:
        logger.warning(
            "プロセス優先度の設定に失敗しました（%s: %s）。スキップします。",
            type(e).__name__,
            e,
        )


def set_cpu_affinity(cpu_count: int | None = None) -> None:
    """カレントプロセスを最初の N コアに固定する。

    Args:
        cpu_count: 使用するコア数。None の場合は設定しない（全コア使用）。
                   利用可能なコア数より大きい場合は全コアを使用する。

    Raises:
        ValueError: cpu_count が 1 未満の場合
    """
    if cpu_count is None:
        return
    if cpu_count < 1:
        raise ValueError(f"cpu_count は 1 以上である必要があります: {cpu_count!r}")
    try:
        p = psutil.Process()
        available = list(range(psutil.cpu_count() or 1))
        pinned = available[:cpu_count]
        if cpu_count > len(available):
            logger.debug(
                "cpu_count=%d が利用可能なコア数 %d を超えています。全コアを使用します。",
                cpu_count,
                len(available),
            )
        p.cpu_affinity(pinned)
        logger.debug("CPU affinity を %r に設定しました (PID=%d)", pinned, p.pid)
    except (psutil.AccessDenied, AttributeError, NotImplementedError) as e:
        logger.warning(
            "CPU affinity の設定に失敗しました（%s: %s）。スキップします。",
            type(e).__name__,
            e,
        )
