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

# Main UX regression checks: every profile has its own editable fields, switch, and status light.
home_fragment_path = root / "app/src/main/java/kittoku/osc/fragment/HomeFragment.kt"
home_fragment = home_fragment_path.read_text(encoding="utf-8") if home_fragment_path.exists() else ""
for anchor in ("Подключения", "Добавить подключение", "refreshSavedConnections",
               "PROFILE_FIELD.", "HOME_HOSTNAME.name", "HOME_USERNAME.name", "HOME_PASSWORD.name",
               "onConnectionChanged", "ACTIVE_PROFILE_NAME", "Переименовать", "Удалить"):
    require(anchor in home_fragment, f"Saved-connections UI is missing: {anchor}")
require("override fun getItemCount() = 1" in activity, "Advanced settings page is still exposed in the main pager")
require("binding.tabBar.visibility = android.view.View.GONE" in activity, "Main screen tabs should be hidden")
card_path = root / "app/src/main/java/kittoku/osc/preference/custom/SavedConnectionPreference.kt"
card = card_path.read_text(encoding="utf-8") if card_path.exists() else ""
for anchor in ("saved_hostname", "saved_username", "saved_password", "saved_connect_switch", "saved_status_dot", "0xFF20A464", "0xFFD64545"):
    require(anchor in card, f"Connection card is missing a field/status indicator: {anchor}")
layout_path = root / "app/src/main/res/layout/preference_saved_connection.xml"
layout = layout_path.read_text(encoding="utf-8") if layout_path.exists() else ""
for anchor in ("Адрес сервера", "Логин", "Пароль", "saved_connect_switch", "saved_status_dot"):
    require(anchor in layout, f"Connection card layout is missing: {anchor}")

# User-facing regressions: login order/label, no technical title, readable theme, original icon.
common_path = root / "app/src/main/java/kittoku/osc/preference/custom/StringPreference.kt"
common = common_path.read_text(encoding="utf-8") if common_path.exists() else ""
require('preferenceTitle = "Логин"' in common, "Login label is missing or not translated")
password_path = root / "app/src/main/java/kittoku/osc/preference/custom/PasswordPreference.kt"
password = password_path.read_text(encoding="utf-8") if password_path.exists() else ""
require('preferenceTitle = "Пароль"' in password, "Password label is missing or not translated")
home_xml_path = root / "app/src/main/res/xml/home.xml"
home_xml = home_xml_path.read_text(encoding="utf-8") if home_xml_path.exists() else ""
require("HomeUsernamePreference" not in home_xml and "HomePasswordPreference" not in home_xml, "Legacy single-profile form should be replaced by repeated connection cards")

require('BuildConfig.VERSION_NAME' not in activity and 'title = "${getString(R.string.app_name)}:' not in activity, "Technical app/version title is still visible")
manifest_path = root / "app/src/main/AndroidManifest.xml"
manifest = manifest_path.read_text(encoding="utf-8") if manifest_path.exists() else ""
require('android:icon="@drawable/ic_sstp_switcher"' in manifest, "Custom SSTP Switcher icon is not configured")
icon_path = root / "app/src/main/res/drawable/ic_sstp_switcher.xml"
require(icon_path.exists(), "Original SSTP Switcher icon resource is missing")
if icon_path.exists():
    icon = icon_path.read_text(encoding="utf-8")
    require("#3978F6" in icon and "#FFFFFF" in icon and "android:pathData" in icon, "S-and-lightning icon artwork is missing")

for theme_path in (
    root / "app/src/main/res/values/themes.xml",
    root / "app/src/main/res/values-night/themes.xml",
):
    if theme_path.exists():
        theme = theme_path.read_text(encoding="utf-8")
        require("Theme.MaterialComponents.Light.NoActionBar" in theme, f"Theme must be light and hide the action bar: {theme_path}")
        require('android:textColorPrimary">#17243A</item>' in theme, f"Primary text contrast is not set: {theme_path}")

if errors:
    print("PRE-BUILD REGRESSION CHECKS FAILED:")
    for error in errors:
        print(f" - {error}")
    sys.exit(1)

print(f"Pre-build checks passed: {len(xml_files)} XML resources parse; critical VPN/profile anchors and Russian labels are present.")
