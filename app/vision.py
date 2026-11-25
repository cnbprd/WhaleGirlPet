# -*- coding: utf-8 -*-
"""v3.0.18：本地多模态输入。

把「屏幕 / 一张图」转成 llama-server 认识的 data URL，喂给带 mmproj 的视觉模型。
缩放是必要的：一张 1080p 截图原样送进去会吃掉几百个 image token，4B 级模型直接答偏。
"""
import base64
import os
import tempfile
import time

MAX_SIDE = 512          # 实测：960px（data url 156KB）被引擎 400 拒收；
                        #       512px（48KB）3.9s 成功，396px 6.1s 也成功
MIN_SIDE = 256
JPEG_Q = 80             # 实测 PNG 原图 2.42MB 直接 400，必须转 JPEG


def _scale(pm):
    """等比缩到 MAX_SIDE 以内（返回 QPixmap；失败就原样返回）。"""
    try:
        w, h = pm.width(), pm.height()
        if max(w, h) <= MAX_SIDE:
            return pm
        k = MAX_SIDE / float(max(w, h))
        from PySide6.QtCore import Qt
        return pm.scaled(max(MIN_SIDE, int(w * k)), max(MIN_SIDE, int(h * k)),
                         Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception:  # noqa: BLE001
        return pm


def capture_screen(path: str = "") -> str:
    """截整屏 → 存 JPEG（不是 PNG），返回路径（失败返回空串）。"""
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            return ""
        screen = app.primaryScreen()
        if screen is None:
            return ""
        pm = screen.grabWindow(0)
        if pm.isNull():
            return ""
        pm = _scale(pm)
        if not path:
            d = tempfile.gettempdir()
            path = os.path.join(d, f"whale_shot_{int(time.time())}.jpg")
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        return path if pm.save(path, "JPG", JPEG_Q) else ""
    except Exception:  # noqa: BLE001
        return ""


def _small_jpeg(path: str) -> bytes:
    """任何图片 → 长边 ≤ MAX_SIDE 的 JPEG 字节。体积要小，否则引擎直接 400。"""
    try:
        from PySide6.QtGui import QImage
        from PySide6.QtCore import Qt
        img = QImage(path)
        if img.isNull():
            with open(path, "rb") as f:
                return f.read()
        if max(img.width(), img.height()) > MAX_SIDE:
            img = img.scaled(MAX_SIDE, MAX_SIDE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        out = os.path.join(tempfile.gettempdir(), "whale_vis_tmp.jpg")
        img.save(out, "JPG", JPEG_Q)
        with open(out, "rb") as f:
            return f.read()
    except Exception:  # noqa: BLE001
        with open(path, "rb") as f:
            return f.read()


def to_data_url(path: str) -> str:
    """图片文件 → data:image/jpeg;base64,...（llama-server 只认 image_url 对象里的这个）。"""
    try:
        if not path or not os.path.exists(path):
            return ""
        raw = _small_jpeg(path)
        return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")
    except Exception:  # noqa: BLE001
        return ""


def vision_message(text: str, image_path: str) -> dict:
    """构一条完整的 OpenAI vision user 消息（返回值直接 append 到 messages 列表）。"""
    url = to_data_url(image_path)
    if not url:
        return {"role": "user", "content": text}
    return {"role": "user", "content": [
        {"type": "text", "text": text},
        {"type": "image_url", "image_url": {"url": url}},
    ]}
