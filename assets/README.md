# 图标资源

`toolbox.spec` 会把应用图标和菜单栏模板图打入应用包。

- `icon.png`：1024 × 1024 的黑白极简应用图标
- `icon.icns`：macOS 应用包图标
- `icon.ico`：Windows 应用图标
- `tray_template.png`：macOS 菜单栏透明底单色模板图

## 重新生成

运行生成脚本会绘制主图标与菜单栏图标，并输出平台格式：

```bash
pip install pillow
python assets/generate_icons.py
```

macOS 上会同时生成 `icon.icns`；其他平台会跳过该格式。托盘图使用独立透明模板，避免将应用图标背景误渲染成菜单栏方块。
