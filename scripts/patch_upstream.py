from pathlib import Path

root = Path("upstream")
strings = root / "app/src/main/res/values/strings.xml"
text = strings.read_text(encoding="utf-8")
text = text.replace(
    '<string name="app_name">Open SSTP Client</string>',
    '<string name="app_name">SSTP Switcher</string>',
)
strings.write_text(text, encoding="utf-8")

menu = root / "app/src/main/res/menu/home_menu.xml"
menu_text = menu.read_text(encoding="utf-8")
for source, target in {
    "Load Profile": "Выбрать подключение",
    "Save Profile": "Добавить подключение",
    "Import Profile": "Импорт профиля",
    "Export Profile": "Экспорт профиля",
    "Reload Defaults": "Сбросить настройки",
}.items():
    menu_text = menu_text.replace(source, target)
menu.write_text(menu_text, encoding="utf-8")

activity = root / "app/src/main/java/kittoku/osc/activity/MainActivity.kt"
text = activity.read_text(encoding="utf-8")

def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Patch failed at {label}: expected one anchor, found {count}")
    return source.replace(old, new, 1)

text = replace_once(
    text,
    "import android.os.Build\n",
    "import android.os.Build\nimport android.os.Handler\nimport android.os.Looper\nimport android.net.VpnService\n",
    "Android imports",
)
text = replace_once(
    text,
    "import kittoku.osc.preference.serializeProfile\n",
    "import kittoku.osc.preference.serializeProfile\nimport kittoku.osc.service.SstpVpnService\nimport kittoku.osc.service.ACTION_VPN_CONNECT\nimport kittoku.osc.service.ACTION_VPN_DISCONNECT\n",
    "VPN service imports",
)

# Activity Result contract is already imported in this upstream file.
text = replace_once(
    text,
    "    private val profileLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->",
    """    private val switchVpnLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == RESULT_OK) startVpnService(ACTION_VPN_CONNECT)
    }

    private val profileLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->""",
    "VPN permission launcher",
)

text = replace_once(
    text,
    """    private fun updatePreferenceView() {""",
    """    private fun startVpnService(action: String) {
        val intent = Intent(this, SstpVpnService::class.java).setAction(action)
        if (action == ACTION_VPN_CONNECT && Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun showSavedProfiles() {
        val profiles = prefs.all
            .filter { it.key.startsWith(PROFILE_KEY_HEADER) && it.value is String }
            .toSortedMap()
        if (profiles.isEmpty()) {
            Toast.makeText(this, "Сначала сохраните профиль через меню «Сохранить профиль»", Toast.LENGTH_LONG).show()
            return
        }
        val keys = profiles.keys.toList()
        val names = keys.map { it.removePrefix(PROFILE_KEY_HEADER) }.toTypedArray()
        AlertDialog.Builder(this)
            .setTitle("Выберите VPN-профиль")
            .setItems(names) { _, index ->
                val serialized = profiles[keys[index]] as? String ?: return@setItems
                val profile = deserializeProfile(serialized)
                if (profile == null) {
                    Toast.makeText(this, "Не удалось прочитать профиль", Toast.LENGTH_SHORT).show()
                    return@setItems
                }
                val wasConnected = prefs.getBoolean(OscPrefKey.HOME_CONNECTOR.name, false)
                if (wasConnected) startVpnService(ACTION_VPN_DISCONNECT)
                importProfile(profile, prefs)
                updatePreferenceView()
                Handler(Looper.getMainLooper()).postDelayed({
                    val permissionIntent = VpnService.prepare(this)
                    if (permissionIntent != null) {
                        switchVpnLauncher.launch(permissionIntent)
                    } else {
                        startVpnService(ACTION_VPN_CONNECT)
                    }
                }, if (wasConnected) 1200L else 150L)
            }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun updatePreferenceView() {""",
    "profile switch implementation",
)

text = replace_once(
    text,
    """            R.id.load_profile -> {
                profileLauncher.launch(Intent(this, BlankActivity::class.java).putExtra(
                    EXTRA_KEY_TYPE,
                    BLANK_ACTIVITY_TYPE_PROFILES
                ))
            }""",
    """            R.id.load_profile -> showSavedProfiles()""",
    "profile menu handler",
)

text = text.replace('0 -> "HOME"', '0 -> "Подключение"')
text = text.replace('1 -> "SETTING"', '1 -> "Настройки"')

activity.write_text(text, encoding="utf-8")
# Visual-only redesign. Keep the existing VPN/profile logic above unchanged.
layout = root / "app/src/main/res/layout/activity_main.xml"
layout_text = layout.read_text(encoding="utf-8")
layout_text = layout_text.replace(
    '    android:orientation="vertical">',
    '    android:orientation="vertical"\n    android:background="@color/screen_background">',
    1,
)
layout_text = layout_text.replace(
    '        android:layout_height="wrap_content" />',
    '        android:layout_height="wrap_content"\n        android:background="@color/surface"\n        android:elevation="2dp"\n        app:tabIndicatorColor="@color/brand_blue"\n        app:tabIndicatorHeight="3dp"\n        app:tabSelectedTextColor="@color/brand_navy"\n        app:tabTextColor="@color/text_secondary" />',
    1,
)
if 'xmlns:app=' not in layout_text:
    layout_text = layout_text.replace(
        '<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"',
        '<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"\n    xmlns:app="http://schemas.android.com/apk/res-auto"',
        1,
    )
layout.write_text(layout_text, encoding="utf-8")

colors = root / "app/src/main/res/values/colors.xml"
colors_text = colors.read_text(encoding="utf-8")
colors_text = colors_text.replace(
    '</resources>',
    '    <color name="brand_navy">#17243A</color>\n'
    '    <color name="brand_navy_dark">#101A2B</color>\n'
    '    <color name="brand_blue">#3978F6</color>\n'
    '    <color name="screen_background">#F3F5F9</color>\n'
    '    <color name="surface">#FFFFFFFF</color>\n'
    '    <color name="text_primary">#17243A</color>\n'
    '    <color name="text_secondary">#68758A</color>\n'
    '</resources>',
)
colors.write_text(colors_text, encoding="utf-8")

theme = root / "app/src/main/res/values/themes.xml"
theme_text = theme.read_text(encoding="utf-8")
theme_text = theme_text.replace(
    '<item name="colorPrimary">@color/teal_700</item>',
    '<item name="colorPrimary">@color/brand_navy</item>',
).replace(
    '<item name="colorPrimaryVariant">@color/teal_700</item>',
    '<item name="colorPrimaryVariant">@color/brand_navy_dark</item>',
).replace(
    '<item name="colorOnPrimary">@color/white</item>',
    '<item name="colorOnPrimary">@color/white</item>',
).replace(
    '<item name="colorSecondary">@color/deep_orange_700</item>',
    '<item name="colorSecondary">@color/brand_blue</item>',
).replace(
    '<item name="colorSecondaryVariant">@color/deep_orange_700</item>',
    '<item name="colorSecondaryVariant">@color/brand_blue</item>',
).replace(
    '<item name="android:statusBarColor">@color/teal_700</item>',
    '<item name="android:statusBarColor">@color/brand_navy_dark</item>',
)
if '<item name="android:windowBackground">' not in theme_text:
    theme_text = theme_text.replace(
        '        <!-- Customize your theme here. -->',
        '        <item name="android:windowBackground">@color/screen_background</item>\n'
        '        <item name="colorControlActivated">@color/brand_blue</item>\n'
        '        <item name="android:fontFamily">sans</item>\n'
        '        <!-- Customize your theme here. -->',
    )
theme.write_text(theme_text, encoding="utf-8")

# Translate visible preference category headings without changing any keys or behavior.
settings = root / "app/src/main/res/xml/settings.xml"
settings_text = settings.read_text(encoding="utf-8")
import re
for source, target in {
    "SSL Layer": "Защита соединения",
    "HTTP Proxy": "Прокси-сервер",
    "PPP Layer": "Параметры соединения",
    "PPP Authentication Protocol": "Авторизация",
    "PPP Network Protocol": "Сетевые протоколы",
    "DNS Server": "DNS-серверы",
    "Routing": "Маршрутизация",
    "Reconnection": "Переподключение",
    "Log": "Журнал событий",
}.items():
    # Replace only visible XML attribute values, never class names, tags, or preference keys.
    settings_text = re.sub(
        r"((?:android:)?title\s*=\s*['\"])" + re.escape(source) + r"(['\"])",
        lambda match: match.group(1) + target + match.group(2),
        settings_text,
    )
settings.write_text(settings_text, encoding="utf-8")


# Fix the login label and keep it in the existing username-before-password order.
common = root / "app/src/main/java/kittoku/osc/preference/custom/StringPreference.kt"
common_text = common.read_text(encoding="utf-8")
if common_text.count('override val preferenceTitle = "Username"') != 1:
    raise SystemExit("Patch failed: expected exactly one Username preference title")
common_text = common_text.replace('override val preferenceTitle = "Username"', 'override val preferenceTitle = "Логин"', 1)
if common_text.count('override val preferenceTitle = "Hostname"') != 1:
    raise SystemExit("Patch failed: expected exactly one Hostname preference title")
common_text = common_text.replace('override val preferenceTitle = "Hostname"', 'override val preferenceTitle = "Адрес сервера"', 1)
common.write_text(common_text, encoding="utf-8")

password_file = root / "app/src/main/java/kittoku/osc/preference/custom/PasswordPreference.kt"
password_text = password_file.read_text(encoding="utf-8")
if password_text.count('override val preferenceTitle = "Password"') != 1:
    raise SystemExit("Patch failed: expected exactly one Password preference title")
password_text = password_text.replace('override val preferenceTitle = "Password"', 'override val preferenceTitle = "Пароль"', 1)
password_file.write_text(password_text, encoding="utf-8")

# Hide the technical app/version string from the top bar while preserving its menu.
activity = root / "app/src/main/java/kittoku/osc/activity/MainActivity.kt"
activity_text = activity.read_text(encoding="utf-8")
activity_text = replace_once(
    activity_text,
    'title = "${getString(R.string.app_name)}: ${BuildConfig.VERSION_NAME}"',
    'title = ""',
    "hide technical title and version",
)
activity.write_text(activity_text, encoding="utf-8")

# Force a light, high-contrast interface even when Android itself uses dark mode.
for theme_path in (
    root / "app/src/main/res/values/themes.xml",
    root / "app/src/main/res/values-night/themes.xml",
):
    if not theme_path.exists():
        continue
    theme_text = theme_path.read_text(encoding="utf-8")
    theme_text = theme_text.replace(
        "Theme.MaterialComponents.DayNight.DarkActionBar",
        "Theme.MaterialComponents.Light.DarkActionBar",
    )
    if '<item name="android:textColorPrimary">' not in theme_text:
        marker = '        <!-- Customize your theme here. -->'
        theme_text = theme_text.replace(
            marker,
            '        <item name="android:textColorPrimary">#17243A</item>\n'
            '        <item name="android:textColorSecondary">#68758A</item>\n'
            '        <item name="android:windowBackground">@color/screen_background</item>\n'
            + marker,
        )
    theme_path.write_text(theme_text, encoding="utf-8")

# Use a distinct original vector icon rather than any SSTP Max branding.
icon = root / "app/src/main/res/drawable/ic_sstp_switcher.xml"
icon.parent.mkdir(parents=True, exist_ok=True)
icon.write_text('''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="48dp"
    android:height="48dp"
    android:viewportWidth="48"
    android:viewportHeight="48">
    <path android:fillColor="#17243A" android:pathData="M24,2 C12,2 4,7 4,7 L4,22 C4,34 13,42 24,46 C35,42 44,34 44,22 L44,7 C44,7 36,2 24,2 Z"/>
    <path android:fillColor="#3978F6" android:pathData="M14,16 L22,16 L22,20 L18,20 L18,28 L22,28 L22,32 L14,32 Z"/>
    <path android:fillColor="#FFFFFF" android:pathData="M26,16 L34,16 L34,20 L30,20 L30,28 L34,28 L34,32 L26,32 Z"/>
    <path android:fillColor="#FFFFFF" android:pathData="M20,22 L28,22 L28,26 L20,26 Z"/>
</vector>
''', encoding="utf-8")
manifest = root / "app/src/main/AndroidManifest.xml"
manifest_text = manifest.read_text(encoding="utf-8")
manifest_text = manifest_text.replace('android:icon="@mipmap/ic_launcher"', 'android:icon="@drawable/ic_sstp_switcher"')
manifest_text = manifest_text.replace('android:roundIcon="@mipmap/ic_launcher_round"', 'android:roundIcon="@drawable/ic_sstp_switcher"')
manifest.write_text(manifest_text, encoding="utf-8")


# Restore the visible login label and remove the unnecessary version title bar.
string_pref = root / "app/src/main/java/kittoku/osc/preference/custom/StringPreference.kt"
string_pref_text = string_pref.read_text(encoding="utf-8")
string_pref_text = replace_once(
    string_pref_text,
    'override val preferenceTitle = "Username"',
    'override val preferenceTitle = "Логин"',
    "login label",
)
string_pref.write_text(string_pref_text, encoding="utf-8")

activity_text = activity.read_text(encoding="utf-8")
activity_text = activity_text.replace(
    '        title = "\${getString(R.string.app_name)}: \${BuildConfig.VERSION_NAME}"\n',
    "",
)
activity_text = activity_text.replace("import kittoku.osc.BuildConfig\n", "")
activity.write_text(activity_text, encoding="utf-8")

# Use an explicitly light, high-contrast theme in both day and night system modes.
for theme_path in (
    root / "app/src/main/res/values/themes.xml",
    root / "app/src/main/res/values-night/themes.xml",
):
    theme_text = theme_path.read_text(encoding="utf-8")
    theme_text = re.sub(
        r'<style name="Theme\.OpenSSTPClient" parent="[^"]+">',
        '<style name="Theme.OpenSSTPClient" parent="Theme.MaterialComponents.Light.NoActionBar">',
        theme_text,
        count=1,
    )
    theme_text = re.sub(r'<item name="colorPrimary">.*?</item>',
        '<item name="colorPrimary">@color/brand_navy</item>', theme_text, count=1)
    theme_text = re.sub(r'<item name="colorPrimaryVariant">.*?</item>',
        '<item name="colorPrimaryVariant">@color/brand_navy_dark</item>', theme_text, count=1)
    theme_text = re.sub(r'<item name="colorOnPrimary">.*?</item>',
        '<item name="colorOnPrimary">@color/white</item>', theme_text, count=1)
    theme_text = re.sub(r'<item name="colorSecondary">.*?</item>',
        '<item name="colorSecondary">@color/brand_blue</item>', theme_text, count=1)
    theme_text = re.sub(r'<item name="colorSecondaryVariant">.*?</item>',
        '<item name="colorSecondaryVariant">@color/brand_blue</item>', theme_text, count=1)
    theme_text = re.sub(r'<item name="android:statusBarColor">.*?</item>',
        '<item name="android:statusBarColor">@color/brand_navy_dark</item>', theme_text, count=1)
    if '<item name="android:textColorPrimary">' not in theme_text:
        theme_text = theme_text.replace(
            '        <!-- Customize your theme here. -->',
            '        <item name="android:textColorPrimary">@color/text_primary</item>\n'
            '        <item name="android:textColorSecondary">@color/text_secondary</item>\n'
            '        <item name="colorOnSurface">@color/text_primary</item>\n'
            '        <item name="colorSurface">@color/surface</item>\n'
            '        <item name="android:windowLightStatusBar">false</item>\n'
            '        <!-- Customize your theme here. -->',
        )
    theme_path.write_text(theme_text, encoding="utf-8")

# A distinct original launcher mark: two endpoints joined by a connection line.
icon = root / "app/src/main/res/drawable/ic_switcher_launcher_foreground.xml"
icon.write_text("""<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path android:fillColor="#00000000" android:strokeColor="#FFFFFF"
        android:strokeWidth="8" android:strokeLineCap="round"
        android:pathData="M30,54 L78,54" />
    <path android:fillColor="#3978F6" android:strokeColor="#FFFFFF"
        android:strokeWidth="4" android:pathData="M30,19 A17,17 0,1 0,30.1 19 Z" />
    <path android:fillColor="#3978F6" android:strokeColor="#FFFFFF"
        android:strokeWidth="4" android:pathData="M78,19 A17,17 0,1 0,78.1 19 Z" />
    <path android:fillColor="#FFFFFF" android:pathData="M30,37 A17,17 0,1 0,30.1 37 Z" />
    <path android:fillColor="#FFFFFF" android:pathData="M78,37 A17,17 0,1 0,78.1 37 Z" />
    <path android:fillColor="#3978F6" android:pathData="M30,43 A11,11 0,1 0,30.1 43 Z" />
    <path android:fillColor="#3978F6" android:pathData="M78,43 A11,11 0,1 0,78.1 43 Z" />
</vector>
""", encoding="utf-8")

for adaptive_name in ("ic_launcher.xml", "ic_launcher_round.xml"):
    adaptive = root / "app/src/main/res/mipmap-anydpi-v26" / adaptive_name
    adaptive.write_text("""<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/brand_navy" />
    <foreground android:drawable="@drawable/ic_switcher_launcher_foreground" />
</adaptive-icon>
""", encoding="utf-8")

# Regenerate legacy launcher PNGs without external packages so older Android versions
# also receive our own icon rather than the upstream artwork.
import math
import struct
import zlib

def make_launcher_png(size):
    scale = 3
    n = size * scale
    navy = (23, 36, 58, 255)
    white = (255, 255, 255, 255)
    blue = (57, 120, 246, 255)
    pixels = bytearray(n * n * 4)
    def put(x, y, color):
        if 0 <= x < n and 0 <= y < n:
            i = (y * n + x) * 4
            pixels[i:i+4] = bytes(color)
    def disk(cx, cy, radius, color):
        r = radius * scale
        x0, x1 = int((cx-radius)*scale), int((cx+radius)*scale)+1
        y0, y1 = int((cy-radius)*scale), int((cy+radius)*scale)+1
        for yy in range(y0, y1):
            for xx in range(x0, x1):
                if (xx-cx*scale)**2 + (yy-cy*scale)**2 <= r*r:
                    put(xx, yy, color)
    def line(x1, y1, x2, y2, thickness, color):
        steps = int(math.hypot((x2-x1)*scale, (y2-y1)*scale)) + 1
        for k in range(steps+1):
            t = k / max(steps, 1)
            disk(x1+(x2-x1)*t, y1+(y2-y1)*t, thickness/2, color)
    radius = size * .22
    for yy in range(n):
        for xx in range(n):
            x, y = xx/scale, yy/scale
            qx = max(radius-x, 0, x-(size-radius))
            qy = max(radius-y, 0, y-(size-radius))
            if qx*qx + qy*qy <= radius*radius or (radius <= x <= size-radius) or (radius <= y <= size-radius):
                put(xx, yy, navy)
    line(size*.30, size*.50, size*.70, size*.50, size*.075, white)
    for cx in (size*.30, size*.70):
        disk(cx, size*.50, size*.16, white)
        disk(cx, size*.50, size*.105, blue)
    out = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            for c in range(4):
                total = sum(pixels[((y*scale+dy)*n + (x*scale+dx))*4+c]
                            for dy in range(scale) for dx in range(scale))
                out[(y*size+x)*4+c] = total // (scale*scale)
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind+data) & 0xffffffff)
    raw = b"".join(b"\x00" + out[y*size*4:(y+1)*size*4] for y in range(size))
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))

for density, size in (("hdpi", 72), ("mdpi", 48), ("xhdpi", 96),
                      ("xxhdpi", 144), ("xxxhdpi", 192)):
    folder = root / "app/src/main/res" / f"mipmap-{density}"
    folder.mkdir(parents=True, exist_ok=True)
    png = make_launcher_png(size)
    (folder / "ic_launcher.png").write_bytes(png)
    (folder / "ic_launcher_round.png").write_bytes(png)

background_color = root / "app/src/main/res/values/ic_launcher_background.xml"
background_color.write_text(
    '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
    '    <color name="ic_launcher_background">#17243A</color>\n</resources>\n',
    encoding="utf-8",
)

# Keep the existing VPN engine and profile operations untouched.
print("Patched Russian UI, profile selector, and visual theme.")
