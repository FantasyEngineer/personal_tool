# Icons

The PyInstaller spec (`toolbox.spec`) looks for these icon files and embeds them
if present; builds still succeed without them (a default Python icon is used).

- `icon.icns` — macOS bundle icon
- `icon.ico`  — Windows exe icon

## How to create them

1. Drop a **square master image** here as `icon.png` (recommended **1024×1024**, RGBA,
   transparent background).
2. Run the generator:

   ```bash
   pip install pillow
   python assets/generate_icons.py
   ```

   This writes `icon.ico` (all platforms) and, on macOS, `icon.icns`.
3. Commit both files so the GitHub Actions build doesn't need to regenerate them.

## Placeholder for now

If you have no artwork yet, you can point at any square PNG and skip the icons —
the app still builds and runs; it just shows the default icon.
