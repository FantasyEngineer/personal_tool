"""文字识别：系统 OCR 命令构造、版面归一化、本地 RapidOCR 与大模型识别的纯逻辑。

除 QImage 的值类型用法外不依赖界面；OCR 运行时的下载地址解析、解压与 ABI 校验
也在这里，进度条/对话框等 UI 流程留在界面层。
"""
import base64
import hashlib
import importlib.util
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import threading
import urllib.request
import zipfile

from PIL import Image
from PyQt5.QtCore import Qt

from toolbox_app.constants import OCR_SETTINGS_PATH
from toolbox_app.natives import win_no_console
from toolbox_app.storage import cache_root
from toolbox_app.kit.updatekit import fetch_version_data, validate_update_url
from toolbox_app.kit.netkit import https_context

OCR_ENGINE_MODES = ("system", "rapidocr", "llm")
OCR_ENGINE_LABELS = {"system": "系统 OCR", "rapidocr": "本地 RapidOCR", "llm": "大模型"}
DEFAULT_OCR_SETTINGS = {"mode": "system", "base_url": "", "api_key": "", "model": ""}


# ---- 系统 OCR --------------------------------------------------------------

def screenshot_ocr_layout_command(image_path):
    """返回带坐标的系统 OCR 命令：输出 {width, height, lines:[{text, words:[...]}]}。

    坐标基于识别图片的像素尺寸，调用方按 width/height 归一化后映射到窗口。
    """
    env = os.environ.copy()
    if platform.system() == "Windows":
        script = r'''
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$stream = $null
$bitmap = $null
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $awaitMethod = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq "AsTask" -and $_.IsGenericMethod -and
        $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1
    } | Select-Object -First 1
    function Await($operation, [Type]$resultType) {
        $task = $awaitMethod.MakeGenericMethod($resultType).Invoke($null, @($operation))
        $task.GetAwaiter().GetResult()
    }
    $ocr = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
    $language = $ocr::AvailableRecognizerLanguages | Where-Object {
        $_.LanguageTag -like "zh-Hans*"
    } | Select-Object -First 1
    if ($null -ne $language) {
        $engine = $ocr::TryCreateFromLanguage($language)
    } else {
        $engine = $ocr::TryCreateFromUserProfileLanguages()
    }
    if ($null -eq $engine) {
        throw "系统没有可用的 OCR 语言包，请在 Windows 设置的语言选项中安装中文或英文语言包。"
    }
    $file = Await ([Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]::GetFileFromPathAsync($env:PERSONAL_TOOLBOX_OCR_IMAGE)) ([Windows.Storage.StorageFile])
    $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $transform = [Windows.Graphics.Imaging.BitmapTransform, Windows.Foundation, ContentType = WindowsRuntime]::new()
    $ratio = [Math]::Min(1.0, [double]$ocr::MaxImageDimension / [Math]::Max($decoder.PixelWidth, $decoder.PixelHeight))
    $transform.ScaledWidth = [uint32][Math]::Max(1, [Math]::Floor($decoder.PixelWidth * $ratio))
    $transform.ScaledHeight = [uint32][Math]::Max(1, [Math]::Floor($decoder.PixelHeight * $ratio))
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync(
        [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8,
        [Windows.Graphics.Imaging.BitmapAlphaMode]::Ignore,
        $transform,
        [Windows.Graphics.Imaging.ExifOrientationMode]::IgnoreExifOrientation,
        [Windows.Graphics.Imaging.ColorManagementMode]::DoNotColorManage
    )) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    $lines = @()
    foreach ($line in $result.Lines) {
        $words = @()
        foreach ($word in $line.Words) {
            $rect = $word.BoundingRect
            $words += [pscustomobject]@{
                t = $word.Text
                x = [double]$rect.X
                y = [double]$rect.Y
                w = [double]$rect.Width
                h = [double]$rect.Height
            }
        }
        $lines += [pscustomobject]@{ text = $line.Text; words = @($words) }
    }
    ConvertTo-Json -InputObject ([pscustomobject]@{
        width = [double]$transform.ScaledWidth
        height = [double]$transform.ScaledHeight
        lines = @($lines)
    }) -Compress -Depth 6
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
} finally {
    if ($null -ne $bitmap) { $bitmap.Dispose() }
    if ($null -ne $stream) { $stream.Dispose() }
}
'''
        env["PERSONAL_TOOLBOX_OCR_IMAGE"] = image_path
        powershell = os.path.join(os.environ["SystemRoot"], "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        return [powershell, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded], env
    if platform.system() == "Darwin":
        script = r'''
ObjC.import('Vision');
ObjC.import('Foundation');
function run(argv) {
    var request = $.VNRecognizeTextRequest.alloc.init;
    request.recognitionLevel = $.VNRequestTextRecognitionLevelAccurate;
    request.usesLanguageCorrection = true;
    var error = Ref();
    // 选择器全名是 ...ForTextRecognitionLevel:revision:error:，漏掉 Text 在 JXA 里
    // 会直接 TypeError: supportedRecognitionLanguagesForRecognitionLevel... is not a function
    var supported = $.VNRecognizeTextRequest.supportedRecognitionLanguagesForTextRecognitionLevelRevisionError(
        request.recognitionLevel, request.revision, error);
    var available = supported.isNil() ? [] : ObjC.deepUnwrap(supported);
    // 顺序很关键：['en-US','zh-Hans'] 会把中文整行漏掉，zh-Hans 要排前面
    var wanted = [];
    ['zh-Hans', 'en-US'].forEach(function(language) {
        if (available.indexOf(language) !== -1 && wanted.indexOf(language) === -1) {
            wanted.push(language);
        }
    });
    // 该 revision 不支持中文时（列表里没有 zh-Hans）退回系统默认，避免整页识别报错
    if (wanted.length > 0) {
        request.recognitionLanguages = wanted;
        if (request.respondsToSelector('setAutomaticallyDetectsLanguage:')) {
            request.automaticallyDetectsLanguage = true;
        }
    }
    var handler = $.VNImageRequestHandler.alloc.initWithURLOptions(
        $.NSURL.fileURLWithPath(argv[0]), $.NSDictionary.dictionary);
    // 必须传 NSArray：直接给 JS 数组 [request] 会触发
    // "exception raised by object: -[__NSDictionaryM frameworkClass]"
    if (!handler.performRequestsError($.NSArray.arrayWithObject(request), error)) {
        throw new Error(ObjC.unwrap(error[0].localizedDescription));
    }
    var lines = [];
    var results = request.results;
    for (var index = 0; index < results.count; index++) {
        var observation = results.objectAtIndex(index);
        var candidate = observation.topCandidates(1).firstObject;
        var box = observation.boundingBox;
        var x = box.origin.x;
        var y = box.origin.y;
        var w = box.size.width;
        var h = box.size.height;
        lines.push({
            text: ObjC.unwrap(candidate.string),
            words: [{ t: ObjC.unwrap(candidate.string), x: x, y: 1 - y - h, w: w, h: h }]
        });
    }
    return JSON.stringify({ width: 1, height: 1, lines: lines });
}
'''
        return ["/usr/bin/osascript", "-l", "JavaScript", "-e", script, image_path], env
    raise RuntimeError("文字识别需要 Windows 10 及以上或 macOS 10.15 及以上的系统 OCR 引擎。")


def join_ocr_spans(spans, line_text=None):
    """拼接同一行的文字片段。

    有整行原文时按词框在原文中的位置切片，能保留英文词间空格；否则按字框间距估算。
    """
    if not spans:
        return ""
    if line_text and all("start" in span and "end" in span for span in spans):
        return line_text[spans[0]["start"]:spans[-1]["end"]].strip()
    text = ""
    previous = None
    for span in spans:
        value = span["t"]
        if not text:
            text = value
        elif previous is not None and span["x"] - (previous["x"] + previous["w"]) > max(
                2.0, 0.3 * min(previous["h"], span["h"])):
            text += " " + value
        else:
            text += value
        previous = span
    return text


def normalize_ocr_layout(layout):
    """把系统 OCR 的 JSON 整理成统一结构：{width, height, lines:[[{t,x,y,w,h}]]}。"""
    if not isinstance(layout, dict):
        raise ValueError("系统 OCR 返回的内容不完整。")
    try:
        width = float(layout.get("width") or 0)
        height = float(layout.get("height") or 0)
    except (TypeError, ValueError):
        raise ValueError("系统 OCR 返回的图片尺寸无效。")
    if width <= 0 or height <= 0:
        raise ValueError("系统 OCR 返回的图片尺寸无效。")
    lines = []
    for line in layout.get("lines") or []:
        if not isinstance(line, dict):
            continue
        words = line.get("words")
        if isinstance(words, dict):
            words = [words]
        spans = []
        for word in words or []:
            if not isinstance(word, dict):
                continue
            text = str(word.get("t") or "")
            try:
                x, y = float(word.get("x")), float(word.get("y"))
                w, h = float(word.get("w")), float(word.get("h"))
            except (TypeError, ValueError):
                continue
            if text and w > 0 and h > 0:
                spans.append({"t": text, "x": x, "y": y, "w": w, "h": h})
        if spans:
            lines.append(spans)
    return {"width": width, "height": height, "lines": lines}


def execute_ocr_layout(image, cancelled, register_process):
    """调用系统 OCR，返回 (layout, error)；失败时 layout 为 None。"""
    try:
        with tempfile.TemporaryDirectory(prefix="toolbox_ocr_") as directory:
            image_path = os.path.join(directory, "selection.png")
            if not image.save(image_path, "PNG"):
                raise RuntimeError("无法写入识别图片，请检查系统临时目录的写入权限。")
            if cancelled.is_set():
                return None, ""
            command, env = screenshot_ocr_layout_command(image_path)
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       env=env, **win_no_console())
            register_process(process)
            if cancelled.is_set():
                process.kill()
            try:
                stdout, stderr = process.communicate(timeout=45)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                raise RuntimeError("识别超过 45 秒，请缩小识别范围后重试。")
            if cancelled.is_set():
                return None, ""
            if process.returncode:
                raise RuntimeError(stderr.decode("utf-8", errors="replace").strip()[:200] or "系统 OCR 识别失败。")
            return normalize_ocr_layout(json.loads(stdout.decode("utf-8-sig"))), ""
    except (OSError, RuntimeError, ValueError) as exc:
        return None, str(exc)
    finally:
        register_process(None)


# ---- 本地 RapidOCR ---------------------------------------------------------

RAPID_OCR_MAX_SIDE = 2560  # 整屏识别时保留足够分辨率，兼顾小字准确率与耗时
_rapidocr_engine = None
_rapidocr_engine_lock = threading.Lock()
_rapidocr_run_lock = threading.Lock()


def rapidocr_available():
    """本地 RapidOCR 是否可用（安装包内置或已按需下载运行时）。"""
    try:
        ocr_runtime_site()
        return (importlib.util.find_spec("rapidocr") is not None
                and importlib.util.find_spec("onnxruntime") is not None)
    except (ImportError, ValueError):
        return False


def rapidocr_version():
    try:
        return importlib.metadata.version("rapidocr")
    except Exception:
        return ""


def _get_rapidocr_engine():
    """懒加载本地引擎：首次初始化约 1～2 秒，之后复用。"""
    global _rapidocr_engine
    if _rapidocr_engine is not None:
        return _rapidocr_engine
    with _rapidocr_engine_lock:
        if _rapidocr_engine is None:
            from rapidocr import RapidOCR
            _rapidocr_engine = RapidOCR(params={
                "Global.log_level": "warning",
                "Global.max_side_len": RAPID_OCR_MAX_SIDE,
            })
    return _rapidocr_engine


def rapidocr_engine():
    """取本地引擎实例（首次调用才初始化，之后复用）。"""
    return _get_rapidocr_engine()


def rapidocr_layout(image_path, cancelled=None):
    """用本地 RapidOCR 识别图片，返回与系统 OCR 相同的版面结构。

    坐标基于原图像素尺寸；优先使用逐词/逐字框，便于在截图预览上精确拖选。
    """
    engine = _get_rapidocr_engine()
    if cancelled is not None and cancelled.is_set():
        raise RuntimeError("已取消")
    with _rapidocr_run_lock:
        result = engine(image_path, return_word_box=True)
    if cancelled is not None and cancelled.is_set():
        raise RuntimeError("已取消")
    with Image.open(image_path) as loaded:
        width, height = loaded.size
    texts = list(result.txts or ())
    word_lines = list(result.word_results or ())
    line_boxes = list(result.boxes) if result.boxes is not None else []
    lines = []
    texts_out = []
    for index, text in enumerate(texts):
        spans = []
        cursor = 0
        for word in word_lines[index] if index < len(word_lines) else ():
            value, box = str(word[0]), word[2]
            xs = [float(point[0]) for point in box]
            ys = [float(point[1]) for point in box]
            if not value.strip() or max(xs) <= min(xs) or max(ys) <= min(ys):
                continue
            # 记录词框在整行原文中的位置，复制时可保留英文词间空格
            found = text.find(value, cursor)
            if found < 0:
                found = cursor
            spans.append({"t": value, "x": min(xs), "y": min(ys),
                          "w": max(xs) - min(xs), "h": max(ys) - min(ys),
                          "start": found, "end": found + len(value)})
            cursor = found + len(value)
        if not spans and text and index < len(line_boxes):
            box = line_boxes[index]
            xs = [float(point[0]) for point in box]
            ys = [float(point[1]) for point in box]
            spans.append({"t": text, "x": min(xs), "y": min(ys),
                          "w": max(xs) - min(xs), "h": max(ys) - min(ys),
                          "start": 0, "end": len(text)})
        if spans:
            lines.append(spans)
            texts_out.append(text)
    return {"width": float(width), "height": float(height), "lines": lines, "texts": texts_out}


def execute_rapidocr_layout(image, cancelled):
    """把 QImage 交给本地 RapidOCR，返回 (layout, error)。"""
    try:
        with tempfile.TemporaryDirectory(prefix="toolbox_rapidocr_") as directory:
            image_path = os.path.join(directory, "screen.png")
            if not image.save(image_path, "PNG"):
                raise RuntimeError("无法写入识别图片，请检查系统临时目录的写入权限。")
            if cancelled.is_set():
                return None, ""
            return rapidocr_layout(image_path, cancelled), ""
    except Exception as exc:  # 模型/运行库异常统一回退系统 OCR
        return None, "本地 RapidOCR 识别失败：%s" % str(exc)[:200]


# ---- 离线运行时管理 --------------------------------------------------------
# 本地 OCR 运行时不随安装包分发（约 100 MB），首次使用时下载到用户目录，
# 这样基础安装包可以保持在几十 MB，且不用的用户完全不用承担体积。

OCR_RUNTIME_FOLDER = "ocr-runtime"
_ocr_runtime_site_cache = None
_ocr_runtime_site_checked = False
_ocr_runtime_migrated = False


def _legacy_ocr_runtime_root():
    """旧版存放位置（Windows: LOCALAPPDATA，macOS: Application Support），仅用于迁移。"""
    if platform.system() == "Darwin":
        base = os.path.expanduser("~/Library/Application Support")
    elif os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, "PersonalToolbox", OCR_RUNTIME_FOLDER)


def _migrate_legacy_ocr_runtime(root):
    """把旧位置的运行时整目录搬到 ~/.personal_toolbox/ocr-runtime，省掉重新下载。"""
    global _ocr_runtime_migrated
    if _ocr_runtime_migrated:
        return
    _ocr_runtime_migrated = True
    legacy = _legacy_ocr_runtime_root()
    if os.path.normcase(legacy) == os.path.normcase(root):
        return
    try:
        if not os.path.isdir(legacy):
            return
        if os.path.isdir(root) and os.listdir(root):
            return                            # 新位置已经有内容，不覆盖
        os.makedirs(os.path.dirname(root), exist_ok=True)
        if os.path.isdir(root):
            try:
                os.rmdir(root)                # 空目录先删掉，避免 rename 目标已存在
            except OSError:
                return
        try:
            os.replace(legacy, root)          # 同一分区时是秒级的目录改名
        except OSError:
            import shutil
            shutil.move(legacy, root)         # 跨分区退化为复制后删除
        # 旧目录空了就顺手清掉，避免 LOCALAPPDATA 下留下空壳
        parent = os.path.dirname(legacy)
        try:
            if os.path.isdir(parent) and not os.listdir(parent):
                os.rmdir(parent)
        except OSError:
            pass
    except OSError:
        pass


def ocr_runtime_root():
    """离线 OCR 运行时的本地目录，与配置缓存同放 ~/.personal_toolbox。"""
    root = os.path.join(cache_root(), OCR_RUNTIME_FOLDER)
    _migrate_legacy_ocr_runtime(root)
    return root


def _ocr_runtime_abi_mismatch(path):
    """运行时目录里编译扩展的 ABI 标签，与当前解释器不一致的返回列表（一致则空）。

    压缩包在发布端按某个 Python 版本编译，扩展模块（.pyd/.so）与解释器强绑定；
    runtime.json 里的 python 字段是本地解压时写的，不能用来判断兼容性。
    """
    current = "cp%d%d" % sys.version_info[:2]
    found = set()
    for base, _dirs, files in os.walk(path):
        for name in files:
            if not name.endswith((".pyd", ".so")):
                continue
            # 两个平台的扩展名后缀不同，两种都要认：
            #   macOS   x.cpython-311-darwin.so
            #   Windows x.cp311-win_amd64.pyd
            for digits in re.findall(r"cpython-([0-9]+)", name):
                found.add("cp" + digits)
            for digits in re.findall(r"cp([0-9]{2,3})", name):
                found.add("cp" + digits)
    return sorted(tag for tag in found if tag != current)


def ocr_runtime_mismatch(path):
    """解压目录里与当前解释器 ABI 不符的标签；一致时返回空列表。"""
    return _ocr_runtime_abi_mismatch(path)


_ocr_runtime_broken = None  # (目录, 不匹配的标签) —— 已下载但与当前解释器不符


def ocr_runtime_abi_issue():
    """已下载的运行库与当前解释器 ABI 不符时返回给用户看的说明，否则空串。"""
    ocr_runtime_site()
    if not _ocr_runtime_broken:
        return ""
    tags = " / ".join(_ocr_runtime_broken[1])
    return ("已下载的离线引擎与当前 Python %d.%d 不匹配（压缩包里是 %s 构建的），"
            "无法加载。请在设置里重新下载（发布端已下载版本若仍不匹配，请改用系统 OCR）。"
            % (sys.version_info[0], sys.version_info[1], tags))


def ocr_runtime_site():
    """已下载且完整的运行时目录；命中时挂到 sys.path 前部，返回目录路径。"""
    global _ocr_runtime_site_cache, _ocr_runtime_site_checked, _ocr_runtime_broken
    if _ocr_runtime_site_checked:
        return _ocr_runtime_site_cache
    _ocr_runtime_site_checked = True
    root = ocr_runtime_root()
    try:
        names = sorted(os.listdir(root), reverse=True)
    except OSError:
        return None
    current = "%d.%d" % sys.version_info[:2]
    for name in names:
        path = os.path.join(root, name)
        try:
            with open(os.path.join(path, "runtime.json"), encoding="utf-8") as file:
                info = json.load(file)
        except (OSError, ValueError):
            continue
        # 扩展模块与解释器版本强绑定，版本不符时宁可不加载
        if not isinstance(info, dict) or info.get("python") != current:
            continue
        required = ["rapidocr", "onnxruntime"]
        if os.name == "nt":
            # Windows 安装包不再自带 numpy（长截图拼接已改纯 Pillow），压缩包里必须
            # 自带一份。早期下载的旧压缩包被 Trim 掉了 numpy，缺它时按「没装」处理，
            # 让应用重新下载，否则 cv2 一 import 就报 No module named 'numpy'。
            required.append("numpy")
        if not all(os.path.isdir(os.path.join(path, package))
                   for package in required):
            continue
        mismatch = _ocr_runtime_abi_mismatch(path)
        if mismatch:
            # 标记（本地写的）与实际扩展 ABI 对不上，别挂到 sys.path 上
            _ocr_runtime_broken = (path, mismatch)
            continue
        if path not in sys.path:
            sys.path.insert(0, path)
        _ocr_runtime_site_cache = path
        return path
    return None


def reset_ocr_runtime_cache():
    global _ocr_runtime_site_cache, _ocr_runtime_site_checked, _ocr_runtime_broken
    _ocr_runtime_site_cache = None
    _ocr_runtime_site_checked = False
    _ocr_runtime_broken = None


def fetch_ocr_runtime_info():
    """从 version.json 取当前平台的离线 OCR 运行时下载信息（多源兜底）。"""
    data = fetch_version_data()
    runtime = data.get("ocr_runtime") if isinstance(data, dict) else None
    if not isinstance(runtime, dict):
        raise ValueError("当前版本还没有提供离线识别引擎。")
    base_key = "macos" if platform.system() == "Darwin" else "windows"
    # 发布端按 Python 版本各产一份运行库（扩展模块与解释器 ABI 强绑定），
    # 先找「平台_主_次」这一份，没有再用平台默认那份。
    keys = ["%s_%d_%d" % (base_key, sys.version_info[0], sys.version_info[1]), base_key]
    item = None
    for key in keys:
        candidate = runtime.get(key)
        if isinstance(candidate, dict) and isinstance(candidate.get("url"), str):
            item = candidate
            break
    if item is None:
        raise ValueError("没有找到当前平台的下载地址。")
    if not getattr(sys, "frozen", False) and keys[0] not in runtime:
        # 源码/pip 运行时的解释器版本常常不是打包机那一版，默认条目对不上 ABI；
        # 与其下 100 MB 再报错，不如直接告诉用户装到自己的环境里。
        raise ValueError(
            "发布端还没有提供 Python %d.%d 版本的离线运行库。\n"
            "源码运行可以直接在当前环境执行 pip install rapidocr onnxruntime，"
            "或在设置里改用系统 OCR。" % (sys.version_info[0], sys.version_info[1]))
    validate_update_url(item["url"])
    try:
        size = int(item.get("size") or 0)
    except (TypeError, ValueError):
        size = 0
    return {"url": item["url"], "sha256": str(item.get("sha256") or "").lower(),
            "size": size, "version": str(runtime.get("version") or data.get("version") or "")}


def extract_runtime_zip(archive, target):
    """把运行时压缩包解到 target；跳过越界路径与 macOS 的资源分支目录。"""
    with zipfile.ZipFile(archive) as bundle:
        root = os.path.realpath(target)
        for info in bundle.infolist():
            name = info.filename.replace("\\", "/").lstrip("/")
            if not name or name.startswith("__MACOSX/"):
                continue
            destination = os.path.realpath(os.path.join(root, name))
            if destination != root and not destination.startswith(root + os.sep):
                continue
            bundle.extract(info, target)


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 256), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---- 大模型识别 ------------------------------------------------------------

LLM_OCR_PROMPT = """请识别这张图片中的所有可见文字，按阅读顺序逐行输出。
只返回 JSON，不要解释，不要 Markdown 代码块，格式如下：
{"lines": [{"text": "这一行的完整文字", "box": [x1, y1, x2, y2]}]}
其中 box 是这行文字的外接矩形，使用相对整张图片宽高的 0 到 1000 的归一化坐标。
尽量保留原文的标点与大小写；没有文字时返回 {"lines": []}。"""


def ocr_llm_ready(settings):
    return bool(settings.get("base_url") and settings.get("api_key")
                and settings.get("model"))


def llm_ocr_layout(image, settings, timeout=90):
    """调用 OpenAI 兼容的多模态接口识别文字，返回与系统 OCR 相同的版面结构。"""
    if image.width() > 2048 or image.height() > 2048:
        image = image.scaled(2048, 2048, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    with tempfile.TemporaryDirectory(prefix="toolbox_llm_ocr_") as directory:
        png_path = os.path.join(directory, "screen.png")
        if not image.save(png_path, "PNG"):
            raise RuntimeError("无法写入识别图片。")
        with open(png_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
    url = settings["base_url"].strip().rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    payload = {
        "model": settings["model"],
        "temperature": 0,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": LLM_OCR_PROMPT},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + encoded}},
        ]}],
    }
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + settings["api_key"]},
        method="POST")
    with urllib.request.urlopen(request, timeout=timeout, context=https_context()) as response:
        data = json.loads(response.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    text = str(content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("模型没有按约定返回 JSON。")
    try:
        result = json.loads(text[start:end + 1])
    except ValueError:
        raise ValueError("模型返回的 JSON 无法解析。")
    lines = []
    for line in (result.get("lines") if isinstance(result, dict) else None) or []:
        if not isinstance(line, dict):
            continue
        value = str(line.get("text") or "").strip()
        box = line.get("box")
        if not value or not isinstance(box, (list, tuple)) or len(box) != 4:
            continue
        try:
            x1, y1, x2, y2 = [float(item) for item in box]
        except (TypeError, ValueError):
            continue
        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))
        if right - left <= 0 or bottom - top <= 0:
            continue
        lines.append([{"t": value, "x": left, "y": top, "w": right - left, "h": bottom - top}])
    if not lines:
        raise ValueError("模型没有返回可用的文字坐标。")
    return {"width": 1000.0, "height": 1000.0, "lines": lines}


# ---- 引擎选择与设置 --------------------------------------------------------

def ocr_mode_hint(mode, settings=None):
    """选中的引擎缺少前置条件时的操作指引（返回空串表示可用）。

    识别过程只按设置执行，绝不自动下载运行库、也不自动改配置，缺东西就交给用户回设置里处理。
    """
    settings = settings if settings is not None else load_ocr_settings()
    if mode == "rapidocr" and not rapidocr_available():
        issue = ocr_runtime_abi_issue()
        if issue:
            return issue + "（识别过程不会自动下载）"
        return ("本地离线引擎尚未下载，无法识别。请打开「设置 → 文字识别」点「下载引擎」下载后再试"
                "（识别过程不会自动下载）。")
    if mode == "llm" and not ocr_llm_ready(settings):
        return ("大模型识别尚未配置完整，无法识别。请打开「设置 → 文字识别」填写接口地址、"
                "API Key 与模型后保存。")
    return ""


def run_ocr(image, cancelled, register_process):
    """按设置中选定的识别引擎执行，不降级、不下载、不改配置。"""
    settings = load_ocr_settings()
    mode = settings.get("mode") or "system"
    hint = ocr_mode_hint(mode, settings)
    if hint:
        return None, OCR_ENGINE_LABELS.get(mode, mode), hint
    if mode == "llm":
        label = "大模型 · " + settings["model"]
        try:
            return llm_ocr_layout(image, settings), label, ""
        except Exception as exc:  # 网络、鉴权、返回格式异常都如实报给用户
            if cancelled.is_set():
                return None, "", ""
            return None, label, "大模型识别失败：%s" % str(exc)[:200]
    if mode == "rapidocr":
        layout, error = execute_rapidocr_layout(image, cancelled)
        if layout is not None:
            return layout, "本地 RapidOCR", ""
        if cancelled.is_set():
            return None, "", ""
        return None, "本地 RapidOCR", error or "本地 RapidOCR 识别失败，请重试。"
    layout, error = execute_ocr_layout(image, cancelled, register_process)
    return layout, "系统 OCR", error


def _legacy_ocr_mode(data):
    """旧版只有 enabled（大模型）/ local_enabled（本地）两个开关，换算成一个引擎选择。"""
    fields = [str(data.get(name) or "").strip() for name in ("base_url", "api_key", "model")]
    if data.get("enabled") and all(fields):
        return "llm"
    if data.get("local_enabled", True) and rapidocr_available():
        return "rapidocr"
    return "system"


def load_ocr_settings():
    """读取文字识别配置；识别引擎由用户在设置里显式选择，缺省为系统 OCR。"""
    settings = dict(DEFAULT_OCR_SETTINGS)
    try:
        with open(OCR_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return settings
    if not isinstance(data, dict):
        return settings
    for key in ("base_url", "api_key", "model"):
        value = data.get(key)
        if isinstance(value, str):
            settings[key] = value.strip()
    mode = data.get("mode")
    settings["mode"] = mode if mode in OCR_ENGINE_MODES else _legacy_ocr_mode(data)
    return settings


def save_ocr_settings(settings):
    os.makedirs(os.path.dirname(OCR_SETTINGS_PATH), exist_ok=True)
    temporary = OCR_SETTINGS_PATH + ".tmp"
    try:
        with open(temporary, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        os.replace(temporary, OCR_SETTINGS_PATH)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
