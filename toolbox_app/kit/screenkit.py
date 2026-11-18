"""长截图拼接与屏幕取图：只算像素，不碰窗口。

纯 Pillow 实现，不依赖 numpy：之前为了做灰度化和相关系数匹配要整份打包
numpy（含 OpenBLAS 共 27 MB），而这里真正需要的只是「灰度化 / 块平均 /
两段图像的相似度」三件事。

匹配度改用平均绝对差（MAD）而不是归一化相关系数：Pillow 的
ImageChops.difference + ImageStat 是 C 实现，1080×900 一对比只要 2 ms
（逐像素的相关系数在纯 Python 里要几十毫秒，没法用）。实测真实截图
滚动拼接的分离度：正确位移 MAD = 0.00，相邻一两行 ≈ 3.5，
完全不相关的画面 ≈ 60~85，阈值仍然好定。

所有函数都以 PIL.Image 为单位（RGB 或灰度 "L"），不再传数组。
"""
from PIL import Image, ImageChops, ImageStat
from PyQt5.QtGui import QImage

# 匹配分数 = 1 - MAD / MAD_SCALE，得分 0.7 对应平均像素差 19.2（0~255 量级）。
# 拼接取的是「最相似的那个位移」，阈值只用来挡「完全没重叠」的情况。
MAD_SCALE = 64.0


def crop_desktop(desktop, rectangle):
    dpr = desktop.devicePixelRatio()
    left, top = round(rectangle.x() * dpr), round(rectangle.y() * dpr)
    right, bottom = round((rectangle.x() + rectangle.width()) * dpr), round((rectangle.y() + rectangle.height()) * dpr)
    image = desktop.copy(left, top, right - left, bottom - top)
    image.setDevicePixelRatio(dpr)
    return image


LONG_SHOT_MAX_HEIGHT = 20000


def qimage_to_image(image):
    """QImage 转 PIL RGB 图（长截图逐帧抓拍的入口）。"""
    converted = image.convertToFormat(QImage.Format_RGB888)
    width, height, stride = converted.width(), converted.height(), converted.bytesPerLine()
    buffer = converted.constBits()
    buffer.setsize(converted.byteCount())
    raw = bytes(buffer)
    if stride != width * 3:
        # QImage 每行有对齐填充，逐行裁掉尾部再交给 Pillow
        raw = b"".join(raw[row * stride:row * stride + width * 3] for row in range(height))
    return Image.frombytes("RGB", (width, height), raw)


def long_shot_missing_deps():
    """长截图启动前预检：现在只依赖 Pillow，Pillow 是必装项，恒为空。

    保留这个入口是因为调用方会先检查再进入抓拍流程：那一步在 Qt 定时器槽里，
    抛 ImportError 会被 PyQt5 转成 qFatal 直接闪退。
    """
    return []


def frame_identical(first, second):
    """两帧是否逐像素完全一致（自动滚动判断是否到底用）。"""
    if first.size != second.size:
        return False
    return ImageChops.difference(first, second).getbbox() is None


def gray_image(rgb):
    """RGB 图转灰度 "L"（长截图拼接用，不依赖 OpenCV）。"""
    return rgb.convert("L")


def block_mean(gray, factor):
    """按 factor 做块平均降采样，粗匹配时把计算量降一个量级。

    Pillow 的 BOX 滤镜就是每个块取算术平均，和原来的 numpy 实现等价。
    """
    if factor <= 1:
        return gray
    width, height = gray.size
    small = (width // factor, height // factor)
    if small[0] <= 0 or small[1] <= 0:
        return gray
    return gray.resize(small, Image.BOX)


def match_score(strip, window):
    """两段等尺寸灰度的相似度：1 完全一致，负数表示平均像素差超过 MAD_SCALE。"""
    mad = ImageStat.Stat(ImageChops.difference(strip, window)).mean[0]
    return 1.0 - mad / MAD_SCALE


def best_vertical_offset(previous, current, top, threshold=0.7):
    """在 current 里找 previous[top:] 的最佳位置，返回新增内容的起始行。"""
    strip = previous.crop((0, top, previous.width, previous.height))
    strip_height = strip.height
    if strip_height < 10 or strip_height >= current.height or current.width != strip.width:
        return None
    best_score, best_offset = -2.0, None
    for offset in range(0, current.height - strip_height + 1):
        score = match_score(strip, current.crop(
            (0, offset, current.width, offset + strip_height)))
        if score > best_score:
            best_score, best_offset = score, offset
    if best_offset is None or best_score < threshold:
        return None
    return best_offset + strip_height


def offset_score(previous, current, top, offset):
    """previous[top:] 落在 current 的 offset 行时的相似度。"""
    strip = previous.crop((0, top, previous.width, previous.height))
    if offset < 0 or offset + strip.height > current.height:
        return -2.0
    return match_score(strip, current.crop(
        (0, offset, current.width, offset + strip.height)))


def stack_images(images):
    """把逐帧抓到的图竖直拼成一张（长截图的最终产物）。"""
    width = max(image.width for image in images)
    height = sum(image.height for image in images)
    merged = Image.new("RGB", (width, height))
    top = 0
    for image in images:
        merged.paste(image, (0, top))
        top += image.height
    return merged
