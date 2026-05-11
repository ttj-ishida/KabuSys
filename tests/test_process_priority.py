# tests/test_process_priority.py
import logging
from unittest.mock import MagicMock, patch

import psutil
import pytest

from kabusys.utils.process_priority import set_cpu_affinity, set_process_priority


class TestSetProcessPriority:
    @pytest.mark.skipif(not hasattr(psutil, "HIGH_PRIORITY_CLASS"), reason="Windows-only constant")
    def test_high_windows(self):
        mock_proc = MagicMock()
        with (
            patch("kabusys.utils.process_priority.platform.system", return_value="Windows"),
            patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc),
        ):
            set_process_priority("high")
            mock_proc.nice.assert_called_once_with(psutil.HIGH_PRIORITY_CLASS)

    @pytest.mark.skipif(
        not hasattr(psutil, "NORMAL_PRIORITY_CLASS"), reason="Windows-only constant"
    )
    def test_normal_windows(self):
        mock_proc = MagicMock()
        with (
            patch("kabusys.utils.process_priority.platform.system", return_value="Windows"),
            patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc),
        ):
            set_process_priority("normal")
            mock_proc.nice.assert_called_once_with(psutil.NORMAL_PRIORITY_CLASS)

    @pytest.mark.skipif(not hasattr(psutil, "IDLE_PRIORITY_CLASS"), reason="Windows-only constant")
    def test_low_windows(self):
        mock_proc = MagicMock()
        with (
            patch("kabusys.utils.process_priority.platform.system", return_value="Windows"),
            patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc),
        ):
            set_process_priority("low")
            mock_proc.nice.assert_called_once_with(psutil.IDLE_PRIORITY_CLASS)

    def test_high_linux(self):
        mock_proc = MagicMock()
        with (
            patch("kabusys.utils.process_priority.platform.system", return_value="Linux"),
            patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc),
        ):
            set_process_priority("high")
            mock_proc.nice.assert_called_once_with(-10)

    def test_normal_linux(self):
        mock_proc = MagicMock()
        with (
            patch("kabusys.utils.process_priority.platform.system", return_value="Linux"),
            patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc),
        ):
            set_process_priority("normal")
            mock_proc.nice.assert_called_once_with(0)

    def test_low_linux(self):
        mock_proc = MagicMock()
        with (
            patch("kabusys.utils.process_priority.platform.system", return_value="Linux"),
            patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc),
        ):
            set_process_priority("low")
            mock_proc.nice.assert_called_once_with(10)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            set_process_priority("realtime")

    def test_access_denied_logs_warning(self, caplog):
        mock_proc = MagicMock()
        mock_proc.nice.side_effect = psutil.AccessDenied(0)
        with (
            patch("kabusys.utils.process_priority.platform.system", return_value="Windows"),
            patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc),
            caplog.at_level(logging.WARNING, logger="kabusys.utils.process_priority"),
        ):
            set_process_priority("high")  # 例外を投げないこと
        assert "AccessDenied" in caplog.text

    def test_attribute_error_logs_warning(self, caplog):
        mock_proc = MagicMock()
        mock_proc.nice.side_effect = AttributeError("nice not supported")
        with (
            patch("kabusys.utils.process_priority.platform.system", return_value="Linux"),
            patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc),
            caplog.at_level(logging.WARNING, logger="kabusys.utils.process_priority"),
        ):
            set_process_priority("high")  # 例外を投げないこと
        assert "AttributeError" in caplog.text

    def test_unsupported_os_logs_warning(self, caplog):
        mock_proc = MagicMock()
        with (
            patch("kabusys.utils.process_priority.platform.system", return_value="OpenBSD"),
            patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc),
            caplog.at_level(logging.WARNING, logger="kabusys.utils.process_priority"),
        ):
            set_process_priority("high")  # 例外を投げないこと
        assert "未対応" in caplog.text
        mock_proc.nice.assert_not_called()

    def test_darwin_uses_nice(self):
        mock_proc = MagicMock()
        with (
            patch("kabusys.utils.process_priority.platform.system", return_value="Darwin"),
            patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc),
        ):
            set_process_priority("high")
            mock_proc.nice.assert_called_once_with(-10)


class TestSetCpuAffinity:
    def test_pins_to_first_n_cores(self):
        mock_proc = MagicMock()
        with (
            patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc),
            patch("kabusys.utils.process_priority.psutil.cpu_count", return_value=4),
        ):
            set_cpu_affinity(2)
            mock_proc.cpu_affinity.assert_called_once_with([0, 1])

    def test_none_skips(self):
        mock_proc = MagicMock()
        with patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc):
            set_cpu_affinity(None)
            mock_proc.cpu_affinity.assert_not_called()

    def test_access_denied_logs_warning(self, caplog):
        mock_proc = MagicMock()
        mock_proc.cpu_affinity.side_effect = psutil.AccessDenied(0)
        with (
            patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc),
            patch("kabusys.utils.process_priority.psutil.cpu_count", return_value=4),
            caplog.at_level(logging.WARNING, logger="kabusys.utils.process_priority"),
        ):
            set_cpu_affinity(2)  # 例外を投げないこと
        assert "AccessDenied" in caplog.text
        assert "CPU affinity" in caplog.text

    def test_attribute_error_logs_warning(self, caplog):
        mock_proc = MagicMock()
        mock_proc.cpu_affinity.side_effect = AttributeError("cpu_affinity not supported")
        with (
            patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc),
            patch("kabusys.utils.process_priority.psutil.cpu_count", return_value=4),
            caplog.at_level(logging.WARNING, logger="kabusys.utils.process_priority"),
        ):
            set_cpu_affinity(2)  # 例外を投げないこと
        assert "AttributeError" in caplog.text

    def test_not_implemented_error_logs_warning(self, caplog):
        mock_proc = MagicMock()
        mock_proc.cpu_affinity.side_effect = NotImplementedError("not supported on this OS")
        with (
            patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc),
            patch("kabusys.utils.process_priority.psutil.cpu_count", return_value=4),
            caplog.at_level(logging.WARNING, logger="kabusys.utils.process_priority"),
        ):
            set_cpu_affinity(2)  # 例外を投げないこと
        assert "NotImplementedError" in caplog.text

    def test_zero_cpu_count_raises(self):
        with pytest.raises(ValueError):
            set_cpu_affinity(0)
