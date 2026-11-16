"""长截图拼接与屏幕取图：只算像素，不碰窗口。

numpy 是长截图的按需依赖，因此所有用到它的函数都在函数体内 import，
避免拖慢启动，也避免在无 numpy 的环境里直接导入失败。
"""
from PyQt5.QtGui import QImage


def crop_desktop(desktop, rectangle):
    dpr = desktop.devicePixelRatio()
    left, top = round(rectangle.x() * dpr), round(rectangle.y() * dpr)
    right, bottom = round((rectangle.x() + rectangle.width()) * dpr), round((rectangle.y() + rectangle.height()) * dpr)
    image = desktop.copy(left, top, right - left, bottom - top)
    image.setDevicePixelRatio(dpr)
    return image


LONG_SHOT_MAX_HEIGHT = 20000


def qimage_rgb_array(image):
    """QImage 转 RGB numpy 数组（长截图拼接用，numpy 按需导入避免拖慢启动）。"""
    import numpy as np
    converted = image.convertToFormat(QImage.Format_RGB888)
    width, height, stride = converted.width(), converted.height(), converted.bytesPerLine()
    buffer = converted.bits()
    buffer.setsize(converted.byteCount())
    array = np.frombuffer(buffer, np.uint8).reshape(height, stride)[:, :width * 3]
    return array.reshape(height, width, 3).copy()


def long_shot_missing_deps():
    """长截图按需依赖 numpy。启动前预检，缺包时返回模块名列表。

    这些 import 发生在 Qt 定时器槽里，一旦抛 ImportError，PyQt5 会调用 qFatal
    直接 abort（表现为闪退），所以必须在进入抓拍流程前先检查并友好提示。
    """
    missing = []
    for name in ("numpy",):
        try:
            __import__(name)
        except ImportError:
            missing.append(name)
    return missing


def gray_array(rgb):
    """RGB 数组转灰度（float32）。长截图拼接用，不依赖 OpenCV。"""
    import numpy as np
    return (rgb[:, :, 0] * 0.299 + rgb[:, :, 1] * 0.587
            + rgb[:, :, 2] * 0.114).astype(np.float32)


def block_mean(gray, factor):
    """按 factor 做块平均降采样，粗匹配时把计算量降一个量级。"""
    if factor <= 1:
        return gray
    height = gray.shape[0] // factor * factor
    width = gray.shape[1] // factor * factor
    if height <= 0 or width <= 0:
        return gray
    blocks = gray[:height, :width].reshape(height // factor, factor,
                                          width // factor, factor)
    return blocks.mean(axis=(1, 3))


def match_score(strip, window):
    """等尺寸两段的归一化相关系数（等价于 OpenCV 的 TM_CCOEFF_NORMED）。"""
    import numpy as np
    a = strip - strip.mean()
    b = window - window.mean()
    denominator = float(np.sqrt((a * a).sum() * (b * b).sum()))
    if denominator <= 1e-6:
        return 0.0
    return float((a * b).sum() / denominator)


def best_vertical_offset(previous, current, top, threshold=0.7):
    """在 current 里找 previous[top:] 的最佳位置，返回新增内容的起始行。"""
    strip = previous[top:]
    height = strip.shape[0]
    if height < 10 or height >= current.shape[0] or current.shape[1] != strip.shape[1]:
        return None
    best_score, best_offset = -2.0, None
    for offset in range(0, current.shape[0] - height + 1):
        score = match_score(strip, current[offset:offset + height])
        if score > best_score:
            best_score, best_offset = score, offset
    if best_offset is None or best_score < threshold:
        return None
    return best_offset + height


def offset_score(previous, current, top, offset):
    """previous[top:] 落在 current 的 offset 行时的相关系数。"""
    strip = previous[top:]
    if offset < 0 or offset + strip.shape[0] > current.shape[0]:
        return -2.0
    return match_score(strip, current[offset:offset + strip.shape[0]])
