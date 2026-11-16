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
from toolbox_app.kit import cryptokit, datetimekit, diffkit

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


if __name__ == "__main__":
    unittest.main()
