"""纯函数回归测试：拆分代码期间保证逻辑不漂移。

只依赖标准库，运行方式：python3 -m unittest discover -s tests -t . -v
"""
import datetime
import hashlib
import os
import ssl
import sys
import tempfile
import os
import unittest
import zoneinfo

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import toolbox
from toolbox_app.kit import (adbkit, barcodekit, convertkit, cronkit, cryptokit, datetimekit,
                             diffkit, netkit, ocrkit, reminderkit, screenkit, updatekit)

UTC = zoneinfo.ZoneInfo("UTC")


class DiffRowsTest(unittest.TestCase):
    """diff_rows / diff_segments / _text_pieces 的行级与字符级结果。"""

    def test_replace(self):
        rows = diffkit.diff_rows("a\nb\nc", "a\nx\nc")
        self.assertEqual([row[0] for row in rows], ["equal", "replace", "equal"])
        self.assertEqual(rows[1], ("replace", 2, "b", 2, "x"))

    def test_insert_and_delete(self):
        rows = diffkit.diff_rows("a\nc", "a\nb\nc")
        self.assertEqual([row[0] for row in rows], ["equal", "insert", "equal"])
        self.assertEqual(rows[1], ("insert", None, "", 2, "b"))

        rows = diffkit.diff_rows("a\nb\nc", "a\nc")
        self.assertEqual([row[0] for row in rows], ["equal", "delete", "equal"])
        self.assertEqual(rows[1], ("delete", 2, "b", None, ""))

    def test_ignore_space_and_case(self):
        rows = diffkit.diff_rows("Hello\nWorld", " hello \n world ",
                                 ignore_space=True, ignore_case=True)
        self.assertEqual([row[0] for row in rows], ["equal", "equal"])

    def test_segments_and_pieces(self):
        self.assertEqual(diffkit.diff_segments("abc", "axc"), ([(1, 2)], [(1, 2)]))
        self.assertEqual(diffkit._text_pieces("abcdef", [(1, 2), (4, 5)]),
                         [("a", False), ("b", True), ("cd", False), ("e", True), ("f", False)])


class CronParseFieldTest(unittest.TestCase):
    """cron 字段解析：取值范围、步长、周日的 7 折算成 0。"""

    parse = staticmethod(cronkit.parse_field)

    def test_star_and_step(self):
        self.assertEqual(self.parse("*", 0, 59), set(range(60)))
        self.assertEqual(self.parse("*/15", 0, 59), {0, 15, 30, 45})
        self.assertEqual(self.parse("0-30/10", 0, 59), {0, 10, 20, 30})
        self.assertEqual(self.parse("5/20", 0, 59), {5, 25, 45})

    def test_single_range_list(self):
        self.assertEqual(self.parse("5", 0, 59), {5})
        self.assertEqual(self.parse("1-5", 1, 31), {1, 2, 3, 4, 5})
        self.assertEqual(self.parse("1,3,5", 0, 59), {1, 3, 5})

    def test_dow_seven_is_sunday(self):
        self.assertEqual(self.parse("7", 0, 7, is_dow=True), {0})
        self.assertEqual(self.parse("0-7", 0, 7, is_dow=True), set(range(7)))

    def test_invalid_tokens(self):
        for token in ("", "60", "0-99", "5-3", "*/0", "1-2-3"):
            with self.assertRaises(ValueError, msg="应拒绝 %r" % token):
                self.parse(token, 0, 59)

    def test_plan_every_minute(self):
        start = datetime.datetime(2026, 11, 16, 9, 30, 15)
        plan = cronkit.plan("* * * * *", 3, now=start)
        self.assertEqual(plan[0], datetime.datetime(2026, 11, 16, 9, 31))
        self.assertEqual([t.minute for t in plan], [31, 32, 33])

    def test_plan_six_fields_with_seconds(self):
        start = datetime.datetime(2026, 11, 16, 9, 30, 15)
        plan = cronkit.plan("*/30 * * * * *", 2, now=start)
        self.assertEqual(plan, [datetime.datetime(2026, 11, 16, 9, 30, 30),
                                datetime.datetime(2026, 11, 16, 9, 31, 0)])

    def test_plan_weekday_and_dow_or_dom(self):
        # 2026-11-16 是周一
        start = datetime.datetime(2026, 11, 16, 8, 0)
        plan = cronkit.plan("0 9 * * 1-5", 1, now=start)
        self.assertEqual(plan[0], datetime.datetime(2026, 11, 16, 9, 0))
        # 日与周同时限定时取“或”：11 号在 2026-11 里是周三，也该命中
        plan = cronkit.plan("0 9 11,22 * 1", 2, now=start)
        self.assertIn(datetime.datetime(2026, 11, 16, 9, 0), plan)

    def test_plan_insufficient(self):
        with self.assertRaises(ValueError):
            cronkit.plan("0 0 30 2 *", 5, now=datetime.datetime(2026, 1, 1))


class BarcodeKitTest(unittest.TestCase):
    """Code 128 编码：值序列、校验位与条/空宽度。"""

    def test_values_and_checksum(self):
        values = barcodekit.code128_values("A")
        # 起始符 104 + (65 - 32)，校验位 = (104 + 1 * 33) % 103
        self.assertEqual(values, [104, 33, (104 + 33) % 103])

    def test_widths_alternate(self):
        widths = barcodekit.code128_widths("HI")
        # 起始符 + 2 个数据 + 校验位共 4 个 symbol（各 11 模块），加 13 模块的结束符
        self.assertEqual(sum(widths), 11 * 4 + 13)

    def test_non_ascii_rejected(self):
        with self.assertRaises(ValueError):
            barcodekit.code128_values("中文")


class UpdateKitTest(unittest.TestCase):
    """版本号解析与下载地址校验。"""

    def test_version_parts(self):
        self.assertEqual(updatekit.update_version_parts("1.2"), (1, 2, 0, 0))
        self.assertEqual(updatekit.update_version_parts("1.2.3.4"), (1, 2, 3, 4))
        for bad in ("", "v1.2", "1.2.3.4.5", "1..2"):
            with self.assertRaises(ValueError):
                updatekit.update_version_parts(bad)

    def test_validate_url(self):
        updatekit.validate_update_url("https://example.com/toolbox.zip")
        for bad in ("http://example.com/a.zip", "https://user@example.com/a.zip",
                    "https://example.com/a.zip#frag", "https://exa mple.com/a.zip", 123):
            with self.assertRaises(ValueError):
                updatekit.validate_update_url(bad)


class NetKitTest(unittest.TestCase):
    """打包后证书库兜底：一定要落到一个真实存在的 PEM 上。"""

    def test_ca_file_points_to_existing_pem(self):
        path = netkit.ca_file()
        self.assertTrue(os.path.isfile(path), path)
        with open(path, "rb") as bundle:
            self.assertIn(b"BEGIN CERTIFICATE", bundle.read(4096))

    def test_missing_env_path_is_skipped(self):
        os.environ["SSL_CERT_FILE"] = "/definitely/not/here.pem"
        try:
            self.assertNotEqual(netkit.ca_file(), "/definitely/not/here.pem")
        finally:
            os.environ.pop("SSL_CERT_FILE", None)

    def test_https_context_verifies(self):
        self.assertEqual(netkit.https_context().verify_mode, ssl.CERT_REQUIRED)


class OcrRuntimeAbiTest(unittest.TestCase):
    """下载的运行库与解释器 ABI 是否一致的判定：mac / win 两种后缀都要认。"""

    def setUp(self):
        current = "cp%d%d" % sys.version_info[:2]
        self.other = "cp312" if current != "cp312" else "cp311"

    def _runtime_dir(self, names):
        folder = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(folder, ignore_errors=True))
        for name in names:
            open(os.path.join(folder, name), "wb").close()
        return folder

    def test_macos_suffix_is_caught(self):
        digits = self.other[2:]
        folder = self._runtime_dir(["a.cpython-%s-darwin.so" % digits])
        self.assertEqual(ocrkit.ocr_runtime_mismatch(folder), [self.other])

    def test_windows_suffix_is_caught(self):
        digits = self.other[2:]
        folder = self._runtime_dir(["a.cp%s-win_amd64.pyd" % digits])
        self.assertEqual(ocrkit.ocr_runtime_mismatch(folder), [self.other])

    def test_matching_interpreter_is_empty(self):
        digits = "%d%d" % sys.version_info[:2]
        folder = self._runtime_dir(["a.cpython-%s-darwin.so" % digits,
                                    "b.cp%s-win_amd64.pyd" % digits])
        self.assertEqual(ocrkit.ocr_runtime_mismatch(folder), [])


class ReminderKitTest(unittest.TestCase):
    """提醒规则的触发时刻计算（QDate/QDateTime 值类型）。"""

    def test_daily_occurrence_and_upcoming(self):
        from PyQt5.QtCore import QDateTime
        now = QDateTime(2026, 11, 16, 9, 0, 0)
        rule = {"time": "08:30", "repeat": reminderkit.REPEAT_DAILY}
        self.assertEqual(reminderkit.reminder_occurrence(rule, now),
                         QDateTime(2026, 11, 16, 8, 30, 0))
        self.assertEqual(reminderkit.reminder_upcoming(rule, now),
                         QDateTime(2026, 11, 17, 8, 30, 0))

    def test_weekday_skips_weekend(self):
        from PyQt5.QtCore import QDateTime
        saturday = QDateTime(2026, 11, 21, 10, 0, 0)  # 周六
        rule = {"time": "09:00", "repeat": reminderkit.REPEAT_WEEKDAY}
        self.assertEqual(reminderkit.reminder_upcoming(rule, saturday),
                         QDateTime(2026, 11, 23, 9, 0, 0))  # 周一

    def test_interval_days(self):
        from PyQt5.QtCore import QDateTime
        rule = {"time": "09:00", "repeat": reminderkit.REPEAT_INTERVAL,
                "every": 2, "unit": "天", "anchor": "2026-11-16"}
        now = QDateTime(2026, 11, 18, 10, 0, 0)
        self.assertEqual(reminderkit.reminder_occurrence(rule, now),
                         QDateTime(2026, 11, 18, 9, 0, 0))
        self.assertEqual(reminderkit.reminder_upcoming(rule, now),
                         QDateTime(2026, 11, 20, 9, 0, 0))
        # 起算日之前没有班次
        before = QDateTime(2026, 11, 15, 10, 0, 0)
        self.assertIsNone(reminderkit.reminder_occurrence(rule, before))

    def test_interval_weeks(self):
        from PyQt5.QtCore import QDateTime
        rule = {"time": "09:00", "repeat": reminderkit.REPEAT_INTERVAL,
                "every": 3, "unit": "周", "anchor": "2026-11-02"}
        now = QDateTime(2026, 11, 20, 0, 0, 0)
        self.assertEqual(reminderkit.reminder_occurrence(rule, now),
                         QDateTime(2026, 11, 2, 9, 0, 0))
        self.assertEqual(reminderkit.reminder_upcoming(rule, now),
                         QDateTime(2026, 11, 23, 9, 0, 0))

    def test_interval_month_clamped_to_month_end(self):
        from PyQt5.QtCore import QDateTime
        rule = {"time": "09:00", "repeat": reminderkit.REPEAT_INTERVAL,
                "every": 1, "unit": "月", "anchor": "2026-01-31"}
        self.assertEqual(reminderkit.reminder_upcoming(rule, QDateTime(2026, 2, 1, 0, 0, 0)),
                         QDateTime(2026, 2, 28, 9, 0, 0))
        # 下一班回到 31 号，不会因为 2 月被钳位就整体漂移
        self.assertEqual(reminderkit.reminder_upcoming(rule, QDateTime(2026, 3, 1, 0, 0, 0)),
                         QDateTime(2026, 3, 31, 9, 0, 0))

    def test_interval_every_two_months_crosses_year(self):
        from PyQt5.QtCore import QDateTime
        rule = {"time": "09:00", "repeat": reminderkit.REPEAT_INTERVAL,
                "every": 2, "unit": "月", "anchor": "2026-11-19"}
        self.assertEqual(reminderkit.reminder_upcoming(rule, QDateTime(2026, 11, 19, 10, 0, 0)),
                         QDateTime(2027, 1, 19, 9, 0, 0))

    def test_interval_preview_points(self):
        from PyQt5.QtCore import QDate, QDateTime
        points = reminderkit.interval_points(QDate(2026, 11, 19), 2, "天", "09:00",
                                             QDateTime(2026, 11, 19, 10, 0, 0), 3)
        self.assertEqual([p.toString("yyyy-MM-dd") for p in points],
                         ["2026-11-21", "2026-11-23", "2026-11-25"])

    def test_invalid_rule_ignored(self):
        from PyQt5.QtCore import QDateTime
        now = QDateTime.currentDateTime()
        self.assertIsNone(reminderkit.reminder_occurrence({"time": "25:00"}, now))
        self.assertIsNone(reminderkit.reminder_upcoming({"time": "abc"}, now))


class PassHashTest(unittest.TestCase):
    """口令哈希的生成与校验：自带盐与参数，能识别篡改。"""

    def test_pbkdf2_roundtrip(self):
        stored = cryptokit.passhash_make("PBKDF2-SHA256", "hunter2")
        self.assertTrue(stored.startswith("$pbkdf2-sha256$"))
        self.assertTrue(cryptokit.passhash_verify(stored, "hunter2"))
        self.assertFalse(cryptokit.passhash_verify(stored, "wrong"))

    @unittest.skipUnless(hasattr(hashlib, "scrypt"),
                         "当前解释器链接的 OpenSSL 没有 scrypt（如 macOS 自带 LibreSSL）")
    def test_scrypt_roundtrip(self):
        stored = cryptokit.passhash_make("scrypt", "hunter2")
        self.assertTrue(stored.startswith("$scrypt$"))
        self.assertTrue(cryptokit.passhash_verify(stored, "hunter2"))
        self.assertFalse(cryptokit.passhash_verify(stored, "wrong"))

    def test_alg_tag(self):
        self.assertEqual(cryptokit.alg_tag("PBKDF2-SHA256"), "pbkdf2-sha256")
        self.assertEqual(cryptokit.alg_tag("scrypt"), "scrypt")

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            cryptokit.passhash_make("PBKDF2-SHA256", "")
        with self.assertRaises(ValueError):
            cryptokit.passhash_parse("$md5$1$abc$def")
        with self.assertRaises(ValueError):
            cryptokit.passhash_verify("", "hunter2")


class DateTimeParseTest(unittest.TestCase):
    """时间解析：时间戳单位自适应、ISO 8601、无时区按指定时区解释。"""

    def test_now(self):
        ns, label = datetimekit.dt_parse("现在", UTC)
        self.assertEqual(label, "当前时间")
        self.assertGreater(ns, 0)

    def test_unix_seconds_and_millis(self):
        ns, label = datetimekit.dt_parse("1700000000", UTC)
        self.assertEqual(ns, 1700000000 * 10 ** 9)
        self.assertIn("秒", label)

        ns, label = datetimekit.dt_parse("1700000000000", UTC)
        self.assertEqual(ns, 1700000000000 * 10 ** 6)
        self.assertIn("毫秒", label)

    def test_explicit_unit(self):
        ns, _ = datetimekit.dt_parse("1700000000", UTC, unit_ns=10 ** 9)
        self.assertEqual(ns, 1700000000 * 10 ** 9)

    def test_iso_with_zone_and_naive_local(self):
        ns, label = datetimekit.dt_parse("2023-11-14T22:13:20Z", UTC)
        self.assertEqual(ns, 1700000000 * 10 ** 9)
        self.assertIn("含时区", label)

        ns2, _ = datetimekit.dt_parse("2023-11-14 22:13:20", UTC)
        self.assertEqual(ns2, ns)

    def test_compact_date_string(self):
        ns, label = datetimekit.dt_parse("20231114", UTC)
        self.assertIn("yyyyMMdd", label)
        self.assertEqual(ns, datetimekit.dt_to_ns(datetime.datetime(2023, 11, 14, tzinfo=UTC)))

    def test_unrecognized_text(self):
        with self.assertRaises(ValueError):
            datetimekit.dt_parse("不是时间", UTC)


class ConvertKitTest(unittest.TestCase):
    """进制换算与单位换算：非法输入要抛错，温度走偏移量而非乘数。"""

    def test_base_convert(self):
        self.assertEqual(convertkit.base_convert("255", 10, 16), "FF")
        self.assertEqual(convertkit.base_convert("0xFF", 16, 10), "255")
        self.assertEqual(convertkit.base_convert("255", 10, 2), "11111111")
        self.assertEqual(convertkit.base_convert("777", 8, 10), "511")
        self.assertEqual(convertkit.base_convert("-1010", 2, 10), "-10")

    def test_base_convert_invalid(self):
        for text in ("", "zz", "12a"):
            with self.assertRaises(ValueError, msg="应拒绝 %r" % text):
                convertkit.base_convert(text, 10, 10)

    def test_unit_format(self):
        self.assertEqual(convertkit.unit_format(1024.0), "1024")
        self.assertEqual(convertkit.unit_format(0.000976562), "0.000976562")

    def test_ratio_and_temp_converters(self):
        to_base, from_base = convertkit.ratio_converters((1, 1024))
        self.assertEqual(to_base[1](2), 2048)
        self.assertEqual(from_base[1](2048), 2)

        to_base, from_base = convertkit.temp_converters()
        self.assertAlmostEqual(to_base[1](212), 100)          # ℉ -> ℃
        self.assertAlmostEqual(from_base[2](100), 373.15)     # ℃ -> K


class ScreenKitTest(unittest.TestCase):
    """长截图拼接：灰度化、块降采样、相似度与垂直配准（纯 Pillow）。"""

    @staticmethod
    def _image(rows, width=4):
        """按行灰度值铺成一张 width 宽的灰度图，贴近真实调用形状。"""
        image = Image.new("L", (width, len(rows)))
        for y, value in enumerate(rows):
            image.paste(value, (0, y, width, y + 1))
        return image

    def test_gray_image(self):
        rgb = Image.new("RGB", (4, 4), (255, 0, 0))     # 纯红 -> 约 76 灰度
        gray = screenkit.gray_image(rgb)
        self.assertEqual(gray.mode, "L")
        self.assertEqual(gray.size, (4, 4))
        self.assertEqual(gray.getpixel((0, 0)), 76)

    def test_block_mean(self):
        gray = Image.new("L", (4, 4))
        for y, row in enumerate(((0, 4, 8, 12),) * 4):
            for x, value in enumerate(row):
                gray.putpixel((x, y), value)
        self.assertEqual(screenkit.block_mean(gray, 1).size, (4, 4))
        small = screenkit.block_mean(gray, 2)
        self.assertEqual(small.size, (2, 2))
        self.assertEqual(small.getpixel((0, 0)), 2)     # mean(0, 4, 0, 4)
        self.assertEqual(small.getpixel((1, 0)), 10)    # mean(8, 12, 8, 12)

    def test_match_score(self):
        strip = self._image(range(20))
        self.assertAlmostEqual(screenkit.match_score(strip, strip), 1.0, places=6)
        inverted = Image.eval(strip, lambda value: 255 - value)
        # 完全反相：平均像素差 255，得分远低于阈值 0.7
        self.assertLess(screenkit.match_score(strip, inverted), 0.0)
        flat = Image.new("L", (4, 20), 128)
        self.assertLess(screenkit.match_score(strip, flat), 0.7)

    def test_best_vertical_offset_and_score(self):
        previous = self._image([0] * 10 + list(range(20, 70)))
        current = self._image(list(range(20, 70)) + [200] * 20)
        # previous[10:] 与 current[0:50] 完全一致，新增内容从第 50 行开始
        self.assertEqual(screenkit.best_vertical_offset(previous, current, 10), 50)
        self.assertAlmostEqual(screenkit.offset_score(previous, current, 10, 0),
                               1.0, places=6)
        self.assertEqual(screenkit.offset_score(previous, current, 10, 60), -2.0)

    def test_frame_identical(self):
        first = self._image(range(6))
        self.assertTrue(screenkit.frame_identical(first, first.copy()))
        self.assertFalse(screenkit.frame_identical(first, self._image(range(1, 7))))
        self.assertFalse(screenkit.frame_identical(first, self._image(range(6), width=8)))

    def test_stack_images(self):
        merged = screenkit.stack_images([self._image([10, 20]), self._image([30])])
        self.assertEqual(merged.size, (4, 3))
        self.assertEqual(merged.mode, "RGB")
        self.assertEqual(merged.getpixel((0, 0)), (10, 10, 10))
        self.assertEqual(merged.getpixel((0, 1)), (20, 20, 20))
        self.assertEqual(merged.getpixel((0, 2)), (30, 30, 30))

    def test_long_shot_missing_deps(self):
        self.assertEqual(screenkit.long_shot_missing_deps(), [])


class AdbKitTest(unittest.TestCase):
    """adbkit 的纯解析逻辑：设备列表、包名列表、状态文案与下载地址。"""

    DEVICES = "List of devices attached\n" \
              "emulator-5554\tdevice product:sdk_gphone64_arm64 model:Pixel_7 device:emu64a\n" \
              "192.168.1.7:5555\tdevice product:panther model:Pixel_7 transport_id:3\n" \
              "RF8M1234ABC\tunauthorized usb:1-1 transport_id:2\n" \
              "RF8M5678DEF\toffline transport_id:4\n" \
              "\n"

    def test_parse_devices(self):
        devices = adbkit.parse_devices(self.DEVICES)
        self.assertEqual([d["serial"] for d in devices],
                         ["emulator-5554", "192.168.1.7:5555", "RF8M1234ABC", "RF8M5678DEF"])
        self.assertEqual(devices[0]["model"], "Pixel_7")
        self.assertEqual(devices[0]["state"], "device")
        self.assertEqual(devices[1]["transport"], "network")
        self.assertEqual(devices[2]["transport"], "usb")
        self.assertEqual(devices[2]["state"], "unauthorized")

    def test_parse_devices_empty_and_header_only(self):
        self.assertEqual(adbkit.parse_devices(""), [])
        self.assertEqual(adbkit.parse_devices("List of devices attached\n\n"), [])

    def test_state_label(self):
        self.assertEqual(adbkit.state_label("device"), "已连接")
        self.assertIn("未授权", adbkit.state_label("unauthorized"))
        self.assertIn("离线", adbkit.state_label("offline"))
        self.assertEqual(adbkit.state_label("weird-state"), "weird-state")

    def test_parse_packages(self):
        text = "package:com.example.app\npackage:com.android.chrome\n" \
               "package:com.example.app\nWarning: something\n"
        self.assertEqual(adbkit.parse_packages(text),
                         ["com.android.chrome", "com.example.app"])

    def test_download_url(self):
        url = adbkit.download_url()
        self.assertTrue(url.startswith("https://dl.google.com/android/repository/platform-tools-latest-"))
        self.assertTrue(url.endswith(".zip"))
        self.assertEqual(adbkit.adb_binary_name(),
                         "adb.exe" if adbkit.platform_key() == "Windows" else "adb")

    def test_is_network_address(self):
        self.assertTrue(adbkit.is_network_address("192.168.1.7:5555"))
        self.assertTrue(adbkit.is_network_address("10.0.0.2"))
        self.assertFalse(adbkit.is_network_address("RF8M1234ABC"))
        self.assertFalse(adbkit.is_network_address(""))

    def test_record_filename(self):
        name = adbkit.record_filename("mp4", "192.168.1.7:5555")
        self.assertTrue(name.startswith("adb-192.168.1.7_5555-"))
        self.assertTrue(name.endswith(".mp4"))
        self.assertNotIn(":", name)
        self.assertTrue(adbkit.record_filename("png").endswith(".png"))

    def test_screen_recorder_args(self):
        recorder = adbkit.ScreenRecorder(
            "/tmp/adb", serial="RF8M1234ABC", remote="/sdcard/a.mp4",
            size="720x1280", bitrate="8M", time_limit=60)
        args = recorder.build_args()
        self.assertEqual(args[:5], ["/tmp/adb", "-s", "RF8M1234ABC", "shell", "screenrecord"])
        self.assertEqual(args[5:], ["--time-limit", "60", "--size", "720x1280",
                                    "--bit-rate", "8M", "/sdcard/a.mp4"])

    def test_screen_recorder_defaults_and_clamp(self):
        recorder = adbkit.ScreenRecorder("/tmp/adb", remote="/sdcard/a.mp4", time_limit=0)
        self.assertEqual(recorder.time_limit, adbkit.ScreenRecorder.MAX_SECONDS)
        args = recorder.build_args()
        self.assertNotIn("--size", args)
        self.assertNotIn("--bit-rate", args)
        self.assertEqual(args[-1], "/sdcard/a.mp4")
        recorder = adbkit.ScreenRecorder("/tmp/adb", remote="/sdcard/a.mp4", time_limit=999)
        self.assertEqual(recorder.time_limit, 180)
        recorder = adbkit.ScreenRecorder("/tmp/adb", remote="/sdcard/a.mp4", time_limit="abc")
        self.assertEqual(recorder.time_limit, 180)
        self.assertFalse(recorder.running())

    def test_default_record_dir(self):
        folder = adbkit.default_record_dir()
        self.assertTrue(os.path.isdir(folder))


if __name__ == "__main__":
    unittest.main()
