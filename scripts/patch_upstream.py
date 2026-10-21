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
    '',
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
        "Theme.MaterialComponents.Light.NoActionBar",
    )
    if '<item name="android:textColorPrimary">' not in theme_text:
        marker = '        <!-- Customize your theme here. -->'
        contrast_items = (
            '        <item name="android:textColorPrimary">#17243A</item>\n'
            '        <item name="android:textColorSecondary">#68758A</item>\n'
        )
        if '<item name="android:windowBackground">' not in theme_text:
            contrast_items += '        <item name="android:windowBackground">@color/screen_background</item>\n'
        theme_text = theme_text.replace(marker, contrast_items + marker)
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



# Show saved connections directly below the connection fields on the main screen.
home_path = root / "app/src/main/java/kittoku/osc/fragment/HomeFragment.kt"
home = home_path.read_text(encoding="utf-8")
home = replace_once(home, "import android.os.Bundle\n",
    "import android.os.Bundle\nimport android.os.Handler\nimport android.os.Looper\nimport android.text.InputType\nimport android.widget.EditText\n",
    "profile list imports")
home = replace_once(home, "import androidx.preference.Preference\n",
    "import androidx.preference.Preference\nimport androidx.preference.PreferenceCategory\nimport androidx.preference.PreferenceManager\nimport androidx.appcompat.app.AlertDialog\n",
    "profile list UI imports")
home = replace_once(home, "import kittoku.osc.preference.OscPrefKey\n",
    "import kittoku.osc.preference.OscPrefKey\nimport kittoku.osc.preference.PROFILE_KEY_HEADER\nimport kittoku.osc.preference.deserializeProfile\nimport kittoku.osc.preference.importProfile\nimport kittoku.osc.preference.serializeProfile\n",
    "profile serialization imports")
home = replace_once(home, "import kittoku.osc.preference.custom.HomeConnectorPreference\n",
    "import kittoku.osc.preference.custom.HomeConnectorPreference\nimport kittoku.osc.preference.custom.OscPreference\n",
    "preference refresh import")
home = replace_once(home,
"""    override fun onCreatePreferences(savedInstanceState: Bundle?, rootKey: String?) {
        setPreferencesFromResource(R.xml.home, rootKey)
    }""",
"""    private lateinit var savedCategory: PreferenceCategory

    override fun onCreatePreferences(savedInstanceState: Bundle?, rootKey: String?) {
        setPreferencesFromResource(R.xml.home, rootKey)
        savedCategory = PreferenceCategory(requireContext()).apply {
            key = "SAVED_CONNECTIONS"
            title = "Сохранённые подключения"
        }
        preferenceScreen.addPreference(savedCategory)
        refreshSavedConnections()
    }""", "saved connection category")
home = replace_once(home, "    private fun startVpnService(action: String) {",
"""    private fun refreshSavedConnections() {
        if (!::savedCategory.isInitialized) return
        val prefs = PreferenceManager.getDefaultSharedPreferences(requireContext())
        savedCategory.removeAll()
        savedCategory.addPreference(Preference(requireContext()).apply {
            key = "ADD_CONNECTION"
            title = "＋ Добавить подключение"
            summary = "Сохранить текущие адрес, логин и пароль"
            order = 0
            setOnPreferenceClickListener {
                showAddConnectionDialog()
                true
            }
        })

        val profiles = prefs.all
            .filter { it.key.startsWith(PROFILE_KEY_HEADER) && it.value is String }
            .toSortedMap()
        if (profiles.isEmpty()) {
            savedCategory.addPreference(Preference(requireContext()).apply {
                key = "NO_SAVED_CONNECTIONS"
                title = "Нет сохранённых подключений"
                summary = "Заполните данные выше и нажмите «Добавить подключение»."
                isSelectable = false
                order = 1
            })
            return
        }

        profiles.entries.forEachIndexed { index, entry ->
            val name = entry.key.removePrefix(PROFILE_KEY_HEADER)
            savedCategory.addPreference(Preference(requireContext()).apply {
                key = "SAVED_CONNECTION_$index"
                title = name
                summary = "Нажмите, чтобы подключиться"
                order = index + 1
                setOnPreferenceClickListener {
                    AlertDialog.Builder(requireContext())
                        .setTitle(name)
                        .setItems(arrayOf("Подключиться", "Переименовать", "Удалить")) { _, action ->
                            when (action) {
                                0 -> activateSavedConnection(entry.key, entry.value as String)
                                1 -> renameSavedConnection(entry.key, name)
                                2 -> AlertDialog.Builder(requireContext())
                                    .setMessage("Удалить подключение «$name»?")
                                    .setPositiveButton("Удалить") { _, _ ->
                                        prefs.edit().remove(entry.key).apply()
                                        refreshSavedConnections()
                                    }
                                    .setNegativeButton("Отмена", null)
                                    .show()
                            }
                        }
                        .setNegativeButton("Отмена", null)
                        .show()
                    true
                }
            })
        }
    }

    private fun showAddConnectionDialog() {
        val prefs = PreferenceManager.getDefaultSharedPreferences(requireContext())
        val hostname = prefs.getString(OscPrefKey.HOME_HOSTNAME.name, "").orEmpty()
        val input = EditText(requireContext()).apply {
            inputType = InputType.TYPE_CLASS_TEXT
            hint = "Например, Ферма 1"
            setText(hostname)
            setSelection(text.length)
        }
        AlertDialog.Builder(requireContext())
            .setTitle("Добавить подключение")
            .setMessage("Задайте имя для списка подключений.")
            .setView(input)
            .setPositiveButton("Сохранить") { _, _ ->
                val name = input.text.toString().trim().ifBlank {
                    hostname.ifBlank { "Подключение" }
                }
                val key = PROFILE_KEY_HEADER + name
                val existed = prefs.contains(key)
                prefs.edit().putString(key, serializeProfile(prefs)).apply()
                refreshSavedConnections()
                android.widget.Toast.makeText(
                    requireContext(),
                    if (existed) "Подключение обновлено" else "Подключение добавлено",
                    android.widget.Toast.LENGTH_SHORT
                ).show()
            }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun renameSavedConnection(oldKey: String, oldName: String) {
        val prefs = PreferenceManager.getDefaultSharedPreferences(requireContext())
        val input = EditText(requireContext()).apply {
            inputType = InputType.TYPE_CLASS_TEXT
            setText(oldName)
            setSelection(text.length)
        }
        AlertDialog.Builder(requireContext())
            .setTitle("Переименовать подключение")
            .setView(input)
            .setPositiveButton("Сохранить") { _, _ ->
                val newName = input.text.toString().trim()
                if (newName.isNotBlank()) {
                    val value = prefs.getString(oldKey, null)
                    if (value != null) {
                        prefs.edit().putString(PROFILE_KEY_HEADER + newName, value)
                            .remove(oldKey).apply()
                        refreshSavedConnections()
                    }
                }
            }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun activateSavedConnection(key: String, serialized: String) {
        val prefs = PreferenceManager.getDefaultSharedPreferences(requireContext())
        val profile = deserializeProfile(serialized) ?: run {
            android.widget.Toast.makeText(requireContext(), "Не удалось прочитать подключение", android.widget.Toast.LENGTH_SHORT).show()
            return
        }
        val wasConnected = prefs.getBoolean(OscPrefKey.HOME_CONNECTOR.name, false)
        if (wasConnected) startVpnService(ACTION_VPN_DISCONNECT)
        importProfile(profile, prefs)
        refreshPreferenceViews()
        Handler(Looper.getMainLooper()).postDelayed({
            if (isAdded) {
                val permissionIntent = VpnService.prepare(requireContext())
                if (permissionIntent != null) preparationLauncher.launch(permissionIntent)
                else startVpnService(ACTION_VPN_CONNECT)
            }
        }, if (wasConnected) 1200L else 150L)
    }

    private fun refreshPreferenceViews() {
        val groups = mutableListOf<androidx.preference.PreferenceGroup>(preferenceScreen)
        while (groups.isNotEmpty()) {
            groups.removeAt(0).forEach { pref ->
                if (pref is OscPreference) pref.updateView()
                if (pref is androidx.preference.PreferenceGroup) groups.add(pref)
            }
        }
        refreshSavedConnections()
    }

    private fun startVpnService(action: String) {""", "saved profile list and actions")
home_path.write_text(home, encoding="utf-8")

# Hide the advanced settings page from the everyday screen without changing VPN defaults.
activity_text = activity.read_text(encoding="utf-8")
activity_text = replace_once(activity_text, "            override fun getItemCount() = 2",
    "            override fun getItemCount() = 1", "single-screen UI")
activity_text = replace_once(activity_text,
"""                return when (position) {
                    0 -> homeFragment
                    1 -> settingFragment
                    else -> throw NotImplementedError(position.toString())
                }""",
"""                return if (position == 0) homeFragment else throw NotImplementedError(position.toString())""",
    "hide advanced settings page")
activity_text = replace_once(activity_text,
"""        }.also {
            binding.pager.adapter = it
        }""",
"""        }.also {
            binding.pager.adapter = it
        }
        binding.tabBar.visibility = android.view.View.GONE""",
    "hide settings tabs")
activity_text = replace_once(activity_text,
"""        TabLayoutMediator(binding.tabBar, binding.pager) { tab, position ->
            tab.text = when (position) {
                0 -> "Подключение"
                1 -> "Настройки"
                else -> throw NotImplementedError(position.toString())
            }
        }.attach()""",
"""        // The main screen contains the connection form and saved profiles.""",
    "remove settings tab")
activity.write_text(activity_text, encoding="utf-8")


# Keep the existing VPN engine and profile operations untouched.
print("Patched Russian UI, profile selector, visual theme, and original icon.")
