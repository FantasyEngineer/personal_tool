"""跨领域常量：版本、更新地址、窗口尺寸与用户目录下的配置文件路径。

只放多个模块都会用到的常量；各工具自己的常量（如 diff 颜色、加密算法表）
跟着对应模块走，避免这里长成第二个大文件。
"""
import os

APP_VERSION = "1.0.66"
UPDATE_CHECK_URL = "https://gitee.com/api/v5/repos/jimmy_hou/personal_tool/contents/version.json?ref=main"

TOOL_WIN_W = 720
TOOL_WIN_H = 480

# 首页工具按钮固定尺寸：窗口变宽时列数变多，而不是把按钮拉宽
LAUNCHER_BTN_W = 96
LAUNCHER_BTN_H = 36
LAUNCHER_GRID_SPACING = 8

HISTORY_LIMIT = 50
JSON_HISTORY_PATH = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "json_history.json")
TOOL_USAGE_HISTORY_PATH = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "tool_usage_history.json")
SEARCH_HISTORY_PATH = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "search_history.json")
SECTION_ORDER_PATH = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "section_order.json")
TOOL_ORDER_PATH = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "tool_order.json")
SHORTCUTS_PATH = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "shortcuts.json")
OCR_SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "ocr_settings.json")
UPDATE_TARGET_PATH = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "update_target.json")

TOOL_RENAMES = {
    "屏幕取色": "取色器", "打卡提醒": "提醒事项", "时间戳": "日期时间",
    "文本对比": "文本工具", "文本统计": "文本工具",
    "二维码": "生成器", "条形码": "生成器", "UUID": "生成器", "随机数": "生成器",
    "Ping 测试": "网络诊断", "DNS 查询": "网络诊断", "路由追踪": "网络诊断",
    "端口扫描": "网络诊断", "网络测速": "网络诊断",
    "JSON/XML": "数据格式", "JSON-YAML": "数据格式", "格式转换": "数据格式",
    "进制转换": "数字转换", "罗马数字": "数字转换", "金额大写": "数字转换",
    "命令速查": "开发速查", "HTTP 状态码": "开发速查",
    "颜色": "颜色转换",
}
SECTION_RENAMES = {
    "系统工具": "系统与桌面", "加解密/编解码": "编码与安全", "文本处理": "文本与数据",
    "时间工具": "时间与日程", "数学工具": "数值计算", "开发工具": "开发辅助",
    "其他": "系统与桌面", "网络诊断": "系统与桌面",
}
