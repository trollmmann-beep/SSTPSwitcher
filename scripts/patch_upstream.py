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



# Replace the one-off form with repeated connection cards: address, login, password, toggle, and a status light.
home_xml = root / "app/src/main/res/xml/home.xml"
home_xml.write_text('''<?xml version="1.0" encoding="utf-8"?>
<PreferenceScreen xmlns:android="http://schemas.android.com/apk/res/android" />
''', encoding="utf-8")

layout_dir = root / "app/src/main/res/layout"
layout_dir.mkdir(parents=True, exist_ok=True)
(layout_dir / "preference_saved_connection.xml").write_text('''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:orientation="vertical"
    android:paddingStart="16dp"
    android:paddingEnd="16dp"
    android:paddingTop="14dp"
    android:paddingBottom="14dp"
    android:background="@drawable/saved_connection_card">
    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:gravity="center_vertical"
        android:orientation="horizontal">
        <TextView
            android:id="@android:id/title"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:textColor="#17243A"
            android:textSize="17sp"
            android:textStyle="bold" />
        <TextView
            android:id="@+id/saved_status_dot"
            android:layout_width="32dp"
            android:layout_height="32dp"
            android:gravity="center"
            android:text="●"
            android:textSize="23sp"
            android:textColor="#D64545" />
    </LinearLayout>
    <EditText
        android:id="@+id/saved_hostname"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:singleLine="true"
        android:inputType="textUri"
        android:hint="Адрес сервера"
        android:textColor="#17243A"
        android:textColorHint="#68758A"
        android:paddingTop="10dp"
        android:paddingBottom="10dp" />
    <EditText
        android:id="@+id/saved_username"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:singleLine="true"
        android:inputType="text"
        android:hint="Логин"
        android:textColor="#17243A"
        android:textColorHint="#68758A"
        android:paddingTop="10dp"
        android:paddingBottom="10dp" />
    <EditText
        android:id="@+id/saved_password"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:singleLine="true"
        android:inputType="textPassword"
        android:hint="Пароль"
        android:textColor="#17243A"
        android:textColorHint="#68758A"
        android:paddingTop="10dp"
        android:paddingBottom="10dp" />
    <androidx.appcompat.widget.SwitchCompat
        android:id="@+id/saved_connect_switch"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Подключение"
        android:textColor="#17243A"
        android:paddingTop="6dp"
        android:paddingBottom="2dp" />
</LinearLayout>
''', encoding="utf-8")
(root / "app/src/main/res/drawable/saved_connection_card.xml").write_text('''<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
    <solid android:color="#FFFFFF" />
    <corners android:radius="14dp" />
    <stroke android:width="1dp" android:color="#DCE3ED" />
</shape>
''', encoding="utf-8")

saved_pref = root / "app/src/main/java/kittoku/osc/preference/custom/SavedConnectionPreference.kt"
saved_pref.write_text('''package kittoku.osc.preference.custom

import android.content.Context
import android.text.InputType
import android.text.TextWatcher
import android.text.Editable
import android.util.AttributeSet
import android.view.View
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.widget.SwitchCompat
import androidx.preference.Preference
import androidx.preference.PreferenceViewHolder
import kittoku.osc.R

internal class SavedConnectionPreference(context: Context) : Preference(context) {
    var hostname: String = ""
    var username: String = ""
    var password: String = ""
    var connected: Boolean = false
    var switchOn: Boolean = false
    var status: Int = 0
    var onFieldsChanged: ((String, String, String) -> Unit)? = null
    var onConnectionChanged: ((Boolean, String, String, String) -> Unit)? = null
    var onManage: (() -> Unit)? = null
    private var statusDot: TextView? = null

    fun updateStatus(newStatus: Int) {
        status = newStatus
        statusDot?.setTextColor(when (newStatus) {
            2 -> 0xFF20A464.toInt()
            1 -> 0xFFFFB020.toInt()
            else -> 0xFFD64545.toInt()
        })
    }

    init {
        layoutResource = R.layout.preference_saved_connection
        isSelectable = false
    }

    override fun onBindViewHolder(holder: PreferenceViewHolder) {
        super.onBindViewHolder(holder)
        val address = holder.findViewById(R.id.saved_hostname) as EditText
        val login = holder.findViewById(R.id.saved_username) as EditText
        val secret = holder.findViewById(R.id.saved_password) as EditText
        val toggle = holder.findViewById(R.id.saved_connect_switch) as SwitchCompat
        val dot = holder.findViewById(R.id.saved_status_dot) as TextView
        val titleView = holder.findViewById(android.R.id.title) as TextView

        address.inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
        login.inputType = InputType.TYPE_CLASS_TEXT
        secret.inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD

        fun bindText(field: EditText, value: String, changed: (String, String, String) -> Unit) {
            field.setText(value)
            field.setOnFocusChangeListener { _, hasFocus ->
                if (!hasFocus) changed(address.text.toString(), login.text.toString(), secret.text.toString())
            }
            field.setOnEditorActionListener { _, _, _ ->
                changed(address.text.toString(), login.text.toString(), secret.text.toString())
                false
            }
        }
        bindText(address, hostname) { h, u, p -> hostname = h; username = u; password = p; onFieldsChanged?.invoke(h, u, p) }
        bindText(login, username) { h, u, p -> hostname = h; username = u; password = p; onFieldsChanged?.invoke(h, u, p) }
        bindText(secret, password) { h, u, p -> hostname = h; username = u; password = p; onFieldsChanged?.invoke(h, u, p) }

        titleView.setOnLongClickListener {
            onManage?.invoke()
            true
        }
        dot.text = "●"
        statusDot = dot
        updateStatus(status)

        toggle.setOnCheckedChangeListener(null)
        toggle.isChecked = switchOn
        toggle.setOnCheckedChangeListener { _, checked ->
            onConnectionChanged?.invoke(checked, address.text.toString(), login.text.toString(), secret.text.toString())
        }
    }
}
''', encoding="utf-8")

home_path = root / "app/src/main/java/kittoku/osc/fragment/HomeFragment.kt"
home = home_path.read_text(encoding="utf-8")
home = replace_once(home, "import android.os.Bundle\n",
    "import android.os.Bundle\nimport android.text.InputType\nimport android.widget.EditText\n",
    "profile card imports")
home = replace_once(home, "import androidx.preference.Preference\n",
    "import androidx.preference.Preference\nimport androidx.preference.PreferenceCategory\nimport androidx.preference.PreferenceManager\nimport androidx.appcompat.app.AlertDialog\n",
    "profile category imports")
home = replace_once(home, "import kittoku.osc.preference.OscPrefKey\n",
    "import kittoku.osc.preference.OscPrefKey\nimport kittoku.osc.preference.PROFILE_KEY_HEADER\nimport kittoku.osc.preference.deserializeProfile\nimport kittoku.osc.preference.importProfile\nimport kittoku.osc.preference.serializeProfile\nimport kittoku.osc.preference.custom.SavedConnectionPreference\n",
    "profile card engine imports")
home = replace_once(home, "import kittoku.osc.preference.custom.HomeConnectorPreference\n",
    "import kittoku.osc.preference.custom.HomeConnectorPreference\nimport kittoku.osc.preference.custom.OscPreference\n",
    "refresh settings import")
home = replace_once(home,
"""    override fun onCreatePreferences(savedInstanceState: Bundle?, rootKey: String?) {
        setPreferencesFromResource(R.xml.home, rootKey)
    }""",
"""    private lateinit var savedCategory: PreferenceCategory

    override fun onCreatePreferences(savedInstanceState: Bundle?, rootKey: String?) {
        setPreferencesFromResource(R.xml.home, rootKey)
        savedCategory = PreferenceCategory(requireContext()).apply {
            key = "SAVED_CONNECTIONS"
            title = "Подключения"
        }
        preferenceScreen.addPreference(savedCategory)
        val prefs = PreferenceManager.getDefaultSharedPreferences(requireContext())
        val savedKeys = prefs.all.keys.filter { it.startsWith(PROFILE_KEY_HEADER) }
        if (savedKeys.isEmpty()) {
            val existingHost = prefs.getString(OscPrefKey.HOME_HOSTNAME.name, "").orEmpty()
            if (existingHost.isNotBlank()) {
                prefs.edit().putString(PROFILE_KEY_HEADER + "Подключение 1", serializeProfile(prefs)).apply()
            }
        }
        refreshSavedConnections()
        val activeName = prefs.getString("ACTIVE_PROFILE_NAME", "").orEmpty()
        if (prefs.getBoolean(OscPrefKey.HOME_CONNECTOR.name, false) && activeName.isNotBlank()) {
            // Reconcile the saved light with the real VPN state after app restart.
            pollConnectionStatus(activeName)
        }
    }""", "profile cards screen")
home = replace_once(home,
"""    private fun attachConnectorListener() {
        findPreference<HomeConnectorPreference>(OscPrefKey.HOME_CONNECTOR.name)!!.also {""",
"""    private fun attachConnectorListener() {
        // Connection switches are rendered per saved profile card.
        findPreference<HomeConnectorPreference>(OscPrefKey.HOME_CONNECTOR.name)?.also {""", "optional legacy connector")
# Remove the legacy connector callback body; the switch no longer exists in home.xml.
home = replace_once(home,
"""        findPreference<HomeConnectorPreference>(OscPrefKey.HOME_CONNECTOR.name)?.also {
            it.onPreferenceChangeListener = Preference.OnPreferenceChangeListener { _, newState ->
                if (newState == true) {
                    checkPreferences(preferenceManager.sharedPreferences!!)?.also { message ->
                        toastInvalidSetting(message, requireContext())
                        return@OnPreferenceChangeListener false
                    }

                    VpnService.prepare(requireContext())?.also { intent ->
                        preparationLauncher.launch(intent)
                    } ?: startVpnService(ACTION_VPN_CONNECT)
                } else {
                    startVpnService(ACTION_VPN_DISCONNECT)
                }

                true
            }
        }""",
"""        // Each profile card owns its own connection toggle.""", "remove legacy global toggle")
home = replace_once(home, "    private fun startVpnService(action: String) {",
"""    private fun refreshSavedConnections() {
        if (!::savedCategory.isInitialized) return
        val prefs = PreferenceManager.getDefaultSharedPreferences(requireContext())
        savedCategory.removeAll()
        val entries = prefs.all.filter { it.key.startsWith(PROFILE_KEY_HEADER) && it.value is String }.toSortedMap()
        entries.keys.forEachIndexed { index, profileKey ->
            val profileName = profileKey.removePrefix(PROFILE_KEY_HEADER)
            val orderKey = "PROFILE_FIELD.$profileName.ORDER"
            if (!prefs.contains(orderKey)) prefs.edit().putInt(orderKey, index).apply()
        }
        val orderedEntries = entries.entries.sortedBy { entry ->
            prefs.getInt("PROFILE_FIELD.${entry.key.removePrefix(PROFILE_KEY_HEADER)}.ORDER", Int.MAX_VALUE)
        }
        orderedEntries.forEach { entry ->
            val name = entry.key.removePrefix(PROFILE_KEY_HEADER)
            val profile = deserializeProfile(entry.value as String)
            val keySuffix = name
            val hostKey = "PROFILE_FIELD.$keySuffix.HOST"
            val loginKey = "PROFILE_FIELD.$keySuffix.LOGIN"
            val passwordKey = "PROFILE_FIELD.$keySuffix.PASSWORD"
            val host = prefs.getString(hostKey, profile?.stringSetting?.get(OscPrefKey.HOME_HOSTNAME.name) ?: "").orEmpty()
            val login = prefs.getString(loginKey, profile?.stringSetting?.get(OscPrefKey.HOME_USERNAME.name) ?: "").orEmpty()
            val password = prefs.getString(passwordKey, profile?.stringSetting?.get(OscPrefKey.HOME_PASSWORD.name) ?: "").orEmpty()
            val activeName = prefs.getString("ACTIVE_PROFILE_NAME", "").orEmpty()
            val connected = prefs.getBoolean(OscPrefKey.HOME_CONNECTOR.name, false) && activeName == name
            val status = prefs.getInt("PROFILE_FIELD.$name.STATUS", if (connected) 1 else 0)
            val card = SavedConnectionPreference(requireContext()).apply {
                key = "CARD_$name"
                title = name
                order = entries.keys.indexOf(entry.key)
                hostname = host
                username = login
                this.password = password
                this.connected = connected
                this.switchOn = connected
                this.status = status
                onFieldsChanged = { h, u, p ->
                    prefs.edit().putString(hostKey, h).putString(loginKey, u).putString(passwordKey, p).apply()
                }
                onConnectionChanged = { enabled, h, u, p ->
                    prefs.edit().putString(hostKey, h).putString(loginKey, u).putString(passwordKey, p).apply()
                    if (enabled) {
                        if (h.isBlank() || u.isBlank() || p.isBlank()) {
                            android.widget.Toast.makeText(requireContext(), "Заполни адрес, логин и пароль", android.widget.Toast.LENGTH_SHORT).show()
                            refreshSavedConnections()
                        } else {
                            prefs.edit().putInt("PROFILE_FIELD.$name.STATUS", 1).apply()
                            refreshSavedConnections()
                            val current = prefs.getBoolean(OscPrefKey.HOME_CONNECTOR.name, false)
                            if (current) startVpnService(ACTION_VPN_DISCONNECT)
                            val chosen = deserializeProfile(prefs.getString(entry.key, "") ?: "")
                            if (chosen == null) {
                                android.widget.Toast.makeText(requireContext(), "Не удалось прочитать профиль", android.widget.Toast.LENGTH_SHORT).show()
                                refreshSavedConnections()
                            } else {
                                chosen.stringSetting[OscPrefKey.HOME_HOSTNAME.name] = h
                                chosen.stringSetting[OscPrefKey.HOME_USERNAME.name] = u
                                chosen.stringSetting[OscPrefKey.HOME_PASSWORD.name] = p
                                importProfile(chosen, prefs)
                                prefs.edit()
                                    .putBoolean(OscPrefKey.HOME_CONNECTOR.name, true)
                                    .putString("ACTIVE_PROFILE_NAME", name)
                                    .apply()
                                refreshPreferenceViews()
                                VpnService.prepare(requireContext())?.also { intent -> preparationLauncher.launch(intent) }
                                    ?: startVpnService(ACTION_VPN_CONNECT)
                                pollConnectionStatus(name)
                                android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({ if (isAdded) refreshSavedConnections() }, 500L)
                            }
                        }
                    } else {
                        if (connected) {
                            prefs.edit().putBoolean(OscPrefKey.HOME_CONNECTOR.name, false)
                                .putInt("PROFILE_FIELD.$name.STATUS", 0).apply()
                            startVpnService(ACTION_VPN_DISCONNECT)
                        }
                        refreshSavedConnections()
                    }
                }
                onManage = { showProfileActions(entry.key, name) }
            }
            savedCategory.addPreference(card)
        }
        savedCategory.addPreference(Preference(requireContext()).apply {
            key = "ADD_CONNECTION"
            title = "＋ Добавить подключение"
            summary = "Добавить ещё один блок с адресом, логином и паролем"
            order = entries.size + 1
            setOnPreferenceClickListener {
                showAddConnectionDialog()
                true
            }
        })
    }

    private fun pollConnectionStatus(name: String, attempt: Int = 0) {
        android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
            if (!isAdded) return@postDelayed
            val prefs = PreferenceManager.getDefaultSharedPreferences(requireContext())
            if (prefs.getString("ACTIVE_PROFILE_NAME", "") != name ||
                !prefs.getBoolean(OscPrefKey.HOME_CONNECTOR.name, false)) return@postDelayed

            val connectivity = requireContext().getSystemService(android.content.Context.CONNECTIVITY_SERVICE)
                as android.net.ConnectivityManager
            // activeNetwork can temporarily point at the underlying Wi-Fi/mobile network.
            // Check all networks so a valid VPN network is not missed during establishment.
            val established = connectivity.allNetworks.any { network ->
                connectivity.getNetworkCapabilities(network)
                    ?.hasTransport(android.net.NetworkCapabilities.TRANSPORT_VPN) == true
            }
            val statusKey = "PROFILE_FIELD.$name.STATUS"
            val card = findPreference<SavedConnectionPreference>("CARD_$name")
            if (established) {
                if (prefs.getInt(statusKey, 0) != 2) {
                    prefs.edit().putInt(statusKey, 2).apply()
                    card?.updateStatus(2)
                }
                // Keep watching while connected so a later VPN drop is reflected in the light.
                pollConnectionStatus(name, 1)
            } else if (attempt >= 45) {
                prefs.edit()
                    .putInt(statusKey, 0)
                    .putBoolean(OscPrefKey.HOME_CONNECTOR.name, false)
                    .apply()
                startVpnService(ACTION_VPN_DISCONNECT)
                refreshSavedConnections()
            } else {
                // Do not rebuild every profile card on every polling tick: that destroys
                // EditText focus and can make Android's long-press Paste menu disappear.
                if (prefs.getInt(statusKey, 0) != 1) {
                    prefs.edit().putInt(statusKey, 1).apply()
                    card?.updateStatus(1)
                }
                pollConnectionStatus(name, attempt + 1)
            }
        }, if (attempt == 0) 800L else 1000L)
    }

    private fun showAddConnectionDialog() {
        val prefs = PreferenceManager.getDefaultSharedPreferences(requireContext())
        val input = EditText(requireContext()).apply {
            inputType = InputType.TYPE_CLASS_TEXT
            hint = "Например, Ферма 2"
        }
        AlertDialog.Builder(requireContext())
            .setTitle("Добавить подключение")
            .setMessage("Укажи название нового блока.")
            .setView(input)
            .setPositiveButton("Добавить") { _, _ ->
                val name = input.text.toString().trim().ifBlank {
                    var number = 1
                    var candidate: String
                    do {
                        candidate = "Подключение $number"
                        number++
                    } while (prefs.contains(PROFILE_KEY_HEADER + candidate))
                    candidate
                }
                val key = PROFILE_KEY_HEADER + name
                if (prefs.contains(key)) {
                    android.widget.Toast.makeText(requireContext(), "Такое имя уже есть", android.widget.Toast.LENGTH_SHORT).show()
                } else {
                    val nextOrder = prefs.all.keys.filter { it.startsWith(PROFILE_KEY_HEADER) }
                        .map { existingKey -> prefs.getInt("PROFILE_FIELD.${existingKey.removePrefix(PROFILE_KEY_HEADER)}.ORDER", -1) }
                        .maxOrNull()?.plus(1) ?: 0
                    prefs.edit()
                        .putString(key, serializeProfile(prefs))
                        .putString("PROFILE_FIELD.$name.HOST", "")
                        .putString("PROFILE_FIELD.$name.LOGIN", "")
                        .putString("PROFILE_FIELD.$name.PASSWORD", "")
                        .putInt("PROFILE_FIELD.$name.ORDER", nextOrder)
                        .putInt("PROFILE_FIELD.$name.STATUS", 0)
                        .apply()
                    refreshSavedConnections()
                }
            }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun showProfileActions(key: String, name: String) {
        val prefs = PreferenceManager.getDefaultSharedPreferences(requireContext())
        AlertDialog.Builder(requireContext())
            .setTitle(name)
            .setItems(arrayOf("Переименовать", "Удалить")) { _, action ->
                if (action == 0) {
                    val input = EditText(requireContext()).apply { setText(name); setSelection(text.length) }
                    AlertDialog.Builder(requireContext()).setTitle("Переименовать подключение").setView(input)
                        .setPositiveButton("Сохранить") { _, _ ->
                            val next = input.text.toString().trim()
                            if (next.isNotBlank() && next != name && !prefs.contains(PROFILE_KEY_HEADER + next)) {
                                val editor = prefs.edit().putString(PROFILE_KEY_HEADER + next, prefs.getString(key, "") ?: "").remove(key)
                                listOf("HOST", "LOGIN", "PASSWORD", "ORDER", "STATUS").forEach { field ->
                                    val old = "PROFILE_FIELD.$name.$field"
                                    val value = prefs.getString(old, null)
                                    if (value != null) editor.putString("PROFILE_FIELD.$next.$field", value)
                                    editor.remove(old)
                                }
                                if (prefs.getString("ACTIVE_PROFILE_NAME", "") == name) editor.putString("ACTIVE_PROFILE_NAME", next)
                                editor.apply()
                                refreshSavedConnections()
                            }
                        }.setNegativeButton("Отмена", null).show()
                } else {
                    AlertDialog.Builder(requireContext()).setMessage("Удалить подключение «$name»?")
                        .setPositiveButton("Удалить") { _, _ ->
                            val editor = prefs.edit().remove(key)
                            listOf("HOST", "LOGIN", "PASSWORD", "ORDER", "STATUS").forEach { editor.remove("PROFILE_FIELD.$name.$it") }
                            if (prefs.getString("ACTIVE_PROFILE_NAME", "") == name) {
                                editor.remove("ACTIVE_PROFILE_NAME").putBoolean(OscPrefKey.HOME_CONNECTOR.name, false)
                                startVpnService(ACTION_VPN_DISCONNECT)
                            }
                            editor.apply()
                            refreshSavedConnections()
                        }.setNegativeButton("Отмена", null).show()
                }
            }.setNegativeButton("Отмена", null).show()
    }

    private fun refreshPreferenceViews() {
        val groups = ArrayDeque<androidx.preference.PreferenceGroup>()
        groups.add(preferenceScreen)
        while (groups.isNotEmpty()) {
            val group = groups.removeFirst()
            for (index in 0 until group.preferenceCount) {
                val pref = group.getPreference(index)
                if (pref is OscPreference) pref.updateView()
                if (pref is androidx.preference.PreferenceGroup) groups.add(pref)
            }
        }
        refreshSavedConnections()
    }

    private fun startVpnService(action: String) {""", "profile card callbacks and management")
home_path.write_text(home, encoding="utf-8")

# Restore the original SSTP Switcher icon used in the earliest builds: blue square, white S and lightning.
icon = root / "app/src/main/res/drawable/ic_sstp_switcher.xml"
icon.write_text('''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#2F6EF2" android:pathData="M0,0h108v108h-108z"/>
    <path android:fillColor="#FFFFFF" android:pathData="M68,28c-4,-4 -10,-6 -17,-6 -13,0 -22,8 -22,19 0,10 7,15 20,18l7,2c7,2 10,4 10,8 0,5 -5,8 -12,8 -8,0 -15,-4 -20,-10l-9,10c7,9 17,14 29,14 16,0 27,-9 27,-22 0,-10 -7,-16 -21,-20l-8,-2c-6,-2 -8,-4 -8,-7 0,-4 4,-7 10,-7 5,0 10,2 14,6z"/>
    <path android:fillColor="#FFFFFF" android:pathData="M77,18l-4,12h8l-7,15 19,-20h-10l4,-7z"/>
</vector>
''', encoding="utf-8")

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

# Preserve Android EditText native long-press selection/paste behavior.
# Do not install custom long-click listeners on editable fields.



print("Patched Russian UI, profile selector, visual theme, and original icon.")
