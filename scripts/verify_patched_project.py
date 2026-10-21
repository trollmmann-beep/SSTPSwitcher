#!/usr/bin/env python3
"""Pre-build regression checks for the patched SSTP Switcher project."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

root = Path("upstream")
errors = []

def require(condition, message):
    if not condition:
        errors.append(message)

# Validate every Android resource XML after patching, catching malformed edits early.
xml_files = list((root / "app/src/main/res").rglob("*.xml"))
require(bool(xml_files), "No Android resource XML files found")
for path in xml_files:
    try:
        ET.parse(path)
    except (ET.ParseError, OSError) as exc:
        errors.append(f"Invalid XML: {path}: {exc}")

activity_path = root / "app/src/main/java/kittoku/osc/activity/MainActivity.kt"
activity = activity_path.read_text(encoding="utf-8") if activity_path.exists() else ""
for anchor in (
    "serializeProfile",
    "deserializeProfile",
    "importProfile(profile, prefs)",
    "SstpVpnService::class.java",
    "ACTION_VPN_CONNECT",
    "ACTION_VPN_DISCONNECT",
    "private fun showSavedProfiles()",
    "R.id.load_profile -> showSavedProfiles()",
):
    require(anchor in activity, f"Missing critical profile/VPN anchor: {anchor}")

menu_path = root / "app/src/main/res/menu/home_menu.xml"
menu = menu_path.read_text(encoding="utf-8") if menu_path.exists() else ""
for label in ("Добавить подключение", "Выбрать подключение", "Импорт профиля", "Экспорт профиля"):
    require(label in menu, f"Missing Russian menu label: {label}")

strings_path = root / "app/src/main/res/values/strings.xml"
strings = strings_path.read_text(encoding="utf-8") if strings_path.exists() else ""
require("SSTP Switcher" in strings, "App name was not changed to SSTP Switcher")

settings_path = root / "app/src/main/res/xml/settings.xml"
settings = settings_path.read_text(encoding="utf-8") if settings_path.exists() else ""
require("Журнал событий" in settings, "Settings headings were not translated")

if errors:
    print("PRE-BUILD REGRESSION CHECKS FAILED:")
    for error in errors:
        print(f" - {error}")
    sys.exit(1)

print(f"Pre-build checks passed: {len(xml_files)} XML resources parse; critical VPN/profile anchors and Russian labels are present.")
