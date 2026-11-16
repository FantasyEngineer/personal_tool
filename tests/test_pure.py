"""纯函数回归测试：拆分代码期间保证逻辑不漂移。

只依赖标准库，运行方式：python3 -m unittest discover -s tests -t . -v
"""
import datetime
import hashlib
import os
import sys
import unittest
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import toolbox
from toolbox_app.kit import convertkit, cryptokit, datetimekit, diffkit, screenkit

try:
    import numpy as np
except ImportError:
    np = None

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

    parse = staticmethod(toolbox.CronWindow._parse_field)

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


@unittest.skipIf(np is None, "长截图拼接依赖 numpy")
class ScreenKitTest(unittest.TestCase):
    """长截图拼接：灰度化、块降采样与相关系数配准。"""

    @staticmethod
    def _rows(values):
        """把一维灰度序列铺成 (H, 1) 的二维数组，贴近真实调用形状。"""
        return np.asarray(values, dtype=np.float32)[:, None]

    def test_gray_array(self):
        rgb = np.zeros((4, 4, 3), dtype=np.uint8)
        rgb[:, :, 0] = 255                       # 纯红 -> 0.299 * 255
        gray = screenkit.gray_array(rgb)
        self.assertEqual(gray.shape, (4, 4))
        self.assertAlmostEqual(float(gray[0, 0]), 76.245, places=3)

    def test_block_mean(self):
        gray = np.arange(16, dtype=np.float32).reshape(4, 4)
        self.assertEqual(screenkit.block_mean(gray, 1).shape, (4, 4))
        small = screenkit.block_mean(gray, 2)
        self.assertEqual(small.shape, (2, 2))
        self.assertAlmostEqual(float(small[0, 0]), 2.5)      # mean(0, 1, 4, 5)

    def test_match_score(self):
        strip = self._rows(range(20))
        self.assertAlmostEqual(screenkit.match_score(strip, strip), 1.0, places=6)
        self.assertAlmostEqual(screenkit.match_score(strip, -strip), -1.0, places=6)
        self.assertEqual(screenkit.match_score(strip, strip * 0), 0.0)

    def test_best_vertical_offset_and_score(self):
        previous = np.zeros((60, 1), dtype=np.float32)
        previous[10:] = self._rows(range(50))
        current = np.zeros((70, 1), dtype=np.float32)
        current[:50] = self._rows(range(50))
        # previous[10:] 与 current[0:50] 完全一致，新增内容从第 50 行开始
        self.assertEqual(screenkit.best_vertical_offset(previous, current, 10), 50)
        self.assertAlmostEqual(screenkit.offset_score(previous, current, 10, 0),
                               1.0, places=6)
        self.assertEqual(screenkit.offset_score(previous, current, 10, 60), -2.0)

    def test_long_shot_missing_deps(self):
        self.assertEqual(screenkit.long_shot_missing_deps(), [])


if __name__ == "__main__":
    unittest.main()
