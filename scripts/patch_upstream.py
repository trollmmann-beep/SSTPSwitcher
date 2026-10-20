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
    "Save Profile": "Сохранить профиль",
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

    private fun showSavedProfilesLegacy() {
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


activity.write_text(text, encoding="utf-8")
print("Patched Russian UI and automatic saved-profile switching.")

# Single-page modern UI. Keep the upstream VPN engine and profile serialization unchanged.
text = text.replace("import android.widget.Toast\n", """import android.widget.Toast
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
""")
text = replace_once(text,
    "    private lateinit var settingFragment: PreferenceFragmentCompat\n",
    "    private lateinit var settingFragment: PreferenceFragmentCompat\n    private lateinit var profileList: LinearLayout\n    private lateinit var statusLabel: TextView\n",
    "modern UI fields")
text = replace_once(text, "    private fun updatePreferenceView() {", """
    private fun showSaveDialogSafe() {
        val form = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(22), dp(8), dp(22), dp(4))
        }
        fun field(hintText: String, value: String = "", type: Int = InputType.TYPE_CLASS_TEXT) =
            android.widget.EditText(this).apply {
                hint = hintText
                setSingleLine(true)
                inputType = type
                setText(value)
                textSize = 16f
                setPadding(dp(12), dp(12), dp(12), dp(12))
                background = pill(Color.rgb(244,246,250), 12)
                layoutParams = LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(10) }
            }
        val nameInput = field("Название, например Ферма 1")
        val hostInput = field("Адрес сервера", "", InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI)
        val portInput = field("Порт SSTP", "443", InputType.TYPE_CLASS_NUMBER)
        val userInput = field("Логин")
        val passInput = field("Пароль", "", InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD)
        form.addView(nameInput)
        form.addView(hostInput)
        form.addView(portInput)
        form.addView(userInput)
        form.addView(passInput)
        val scroll = ScrollView(this).apply { addView(form) }
        AlertDialog.Builder(this)
            .setTitle("Новое подключение")
            .setMessage("Введите данные SSTP-сервера")
            .setView(scroll)
            .setPositiveButton("Сохранить", null)
            .setNegativeButton("Отмена", null)
            .create().also { dialog ->
                dialog.setOnShowListener {
                    dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                        val profileName = nameInput.text.toString().trim()
                        val hostname = hostInput.text.toString().trim()
                        val port = portInput.text.toString().trim().toIntOrNull()
                        val username = userInput.text.toString()
                        val password = passInput.text.toString()
                        when {
                            profileName.isBlank() -> nameInput.error = "Введите название"
                            hostname.isBlank() -> hostInput.error = "Введите адрес сервера"
                            port == null || port !in 1..65535 -> portInput.error = "Порт от 1 до 65535"
                            username.isBlank() -> userInput.error = "Введите логин"
                            password.isBlank() -> passInput.error = "Введите пароль"
                            else -> {
                                prefs.edit()
                                    .putString(OscPrefKey.HOME_HOSTNAME.name, hostname)
                                    .putInt(OscPrefKey.SSL_PORT.name, port)
                                    .putString(OscPrefKey.HOME_USERNAME.name, username)
                                    .putString(OscPrefKey.HOME_PASSWORD.name, password)
                                    .putBoolean(OscPrefKey.HOME_CONNECTOR.name, false)
                                    .apply()
                                prefs.edit()
                                    .putString(PROFILE_KEY_HEADER + profileName, serializeProfile(prefs))
                                    .apply()
                                refreshProfiles()
                                Toast.makeText(this, "Подключение сохранено", Toast.LENGTH_SHORT).show()
                                dialog.dismiss()
                            }
                        }
                    }
                }
                dialog.show()
            }
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()
    private fun uiText(s: String, size: Float, color: Int, bold: Boolean = false) = TextView(this).apply {
        text = s; textSize = size; setTextColor(color)
        if (bold) typeface = Typeface.create("sans-serif", Typeface.BOLD)
    }
    private fun pill(color: Int, radius: Int) = GradientDrawable().apply {
        setColor(color); cornerRadius = dp(radius).toFloat()
    }
    private fun selectProfile(key: String) {
        val serialized = prefs.getString(key, null) ?: return
        val profile = deserializeProfile(serialized) ?: run {
            Toast.makeText(this, "Не удалось прочитать профиль", Toast.LENGTH_SHORT).show(); return
        }
        val wasConnected = prefs.getBoolean(OscPrefKey.HOME_CONNECTOR.name, false)
        if (wasConnected) startVpnService(ACTION_VPN_DISCONNECT)
        importProfile(profile, prefs)
        statusLabel.text = "Подключение запускается…"
        refreshProfiles()
        Handler(Looper.getMainLooper()).postDelayed({
            val permission = VpnService.prepare(this)
            if (permission != null) switchVpnLauncher.launch(permission) else startVpnService(ACTION_VPN_CONNECT)
        }, if (wasConnected) 1200L else 150L)
    }
    private fun refreshProfiles() {
        if (!::profileList.isInitialized) return
        profileList.removeAllViews()
        val profiles = prefs.all.filter { it.key.startsWith(PROFILE_KEY_HEADER) && it.value is String }.toSortedMap()
        if (profiles.isEmpty()) {
            profileList.addView(uiText("Сохранённых подключений пока нет", 14f, Color.rgb(110,118,132)).apply {
                gravity = Gravity.CENTER; setPadding(0, dp(28), 0, dp(28))
            })
        }
        profiles.forEach { (key, _) ->
            val card = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL
                setPadding(dp(16), dp(16), dp(16), dp(16)); background = pill(Color.WHITE, 18)
                elevation = dp(1).toFloat()
            }
            val info = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL
                layoutParams = LinearLayout.LayoutParams(0, -2, 1f) }
            info.addView(uiText(key.removePrefix(PROFILE_KEY_HEADER), 16f, Color.rgb(28,33,43), true))
            info.addView(uiText("SSTP · Сохранённый профиль", 12f, Color.rgb(116,123,136)).apply {
                setPadding(0, dp(5), 0, 0)
            })
            card.addView(info)
            val profileSwitch = android.widget.Switch(this).apply {
                val saved = prefs.getString(key, null)?.let { deserializeProfile(it) }
                val savedHost = saved?.stringSetting?.get(OscPrefKey.HOME_HOSTNAME.name).orEmpty()
                val currentHost = getStringPrefValue(OscPrefKey.HOME_HOSTNAME, prefs)
                isChecked = prefs.getBoolean(OscPrefKey.HOME_CONNECTOR.name, false) && savedHost == currentHost
                contentDescription = "Включить подключение ${key.removePrefix(PROFILE_KEY_HEADER)}"
                setOnCheckedChangeListener { _, enabled ->
                    if (enabled) {
                        selectProfile(key)
                    } else if (savedHost == getStringPrefValue(OscPrefKey.HOME_HOSTNAME, prefs) &&
                        prefs.getBoolean(OscPrefKey.HOME_CONNECTOR.name, false)) {
                        startVpnService(ACTION_VPN_DISCONNECT)
                        statusLabel.text = "Отключение…"
                    }
                }
            }
            card.addView(profileSwitch)
            card.setOnClickListener { selectProfile(key) }
            profileList.addView(card, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(10) })
        }
    }
    private fun showSavedProfiles() { refreshProfiles() }

    private fun updatePreferenceView() {""", "single-page profile list")
text = replace_once(text, """        title = "${getString(R.string.app_name)}: ${BuildConfig.VERSION_NAME}"
        val binding = ActivityMainBinding.inflate(layoutInflater)
        binding.root.fitsSystemWindows = true
        setContentView(binding.root)

        prefs = PreferenceManager.getDefaultSharedPreferences(this)
        homeFragment = HomeFragment()
        settingFragment = SettingFragment()

        object : FragmentStateAdapter(this) {
            override fun getItemCount() = 2

            override fun createFragment(position: Int): Fragment {
                return when (position) {
                    0 -> homeFragment
                    1 -> settingFragment
                    else -> throw NotImplementedError(position.toString())
                }
            }
        }.also {
            binding.pager.adapter = it
        }


        TabLayoutMediator(binding.tabBar, binding.pager) { tab, position ->
            tab.text = when (position) {
                0 -> "HOME"
                1 -> "SETTING"
                else -> throw NotImplementedError(position.toString())
            }
        }.attach()
""", """        title = getString(R.string.app_name)
        prefs = PreferenceManager.getDefaultSharedPreferences(this)
        homeFragment = HomeFragment()
        settingFragment = SettingFragment()
        val page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(20), dp(20), dp(14))
            setBackgroundColor(Color.rgb(246,247,251))
        }
        val header = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        header.addView(TextView(this).apply {
            text = "S"; textSize = 24f; typeface = Typeface.DEFAULT_BOLD; gravity = Gravity.CENTER
            setTextColor(Color.WHITE)
            background = GradientDrawable(GradientDrawable.Orientation.TL_BR,
                intArrayOf(Color.rgb(47,110,242), Color.rgb(90,75,225))).apply { cornerRadius = dp(16).toFloat() }
            layoutParams = LinearLayout.LayoutParams(dp(52), dp(52))
        })
        val titleBlock = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(12),0,0,0) }
        titleBlock.addView(uiText("SSTP Switcher", 22f, Color.rgb(22,28,40), true))
        titleBlock.addView(uiText("Ваши VPN-подключения", 13f, Color.rgb(116,123,136)).apply { setPadding(0,dp(3),0,0) })
        header.addView(titleBlock); page.addView(header)
        page.addView(uiText("Подключения", 18f, Color.rgb(34,40,52), true).apply {
            setPadding(0,dp(24),0,dp(12))
        })
        statusLabel = uiText("Выберите подключение из списка", 13f, Color.rgb(100,110,126)).apply {
            setPadding(dp(14),dp(12),dp(14),dp(12)); background = pill(Color.rgb(232,238,250),14)
        }
        page.addView(statusLabel)
        val scroll = ScrollView(this)
        profileList = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(0,dp(14),0,dp(10)) }
        scroll.addView(profileList); page.addView(scroll, LinearLayout.LayoutParams(-1,0,1f))
        page.addView(TextView(this).apply {
            text = "+  Сохранить текущее подключение"; textSize = 15f; typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER; setTextColor(Color.WHITE); background = pill(Color.rgb(43,101,232),17)
            setPadding(dp(16),dp(16),dp(16),dp(16)); setOnClickListener { showSaveDialogSafe() }
        })
        setContentView(page)
        refreshProfiles()
""", "replace tabbed home screen")
text = text.replace('Toast.makeText(this, "PROFILE SAVED", Toast.LENGTH_SHORT).show()', 'refreshProfiles()\n                Toast.makeText(this, "Подключение сохранено", Toast.LENGTH_SHORT).show()')
text = text.replace('Toast.makeText(this, "PROFILE IMPORTED", Toast.LENGTH_SHORT).show()', 'refreshProfiles()\n                Toast.makeText(this, "Профиль импортирован", Toast.LENGTH_SHORT).show()')
activity.write_text(text, encoding="utf-8")
print("Modern single-page profile list applied.")

# Original launcher mark: blue rounded tile with a white signal/route glyph.
manifest = root / "app/src/main/AndroidManifest.xml"
manifest_text = manifest.read_text(encoding="utf-8").replace('@mipmap/ic_launcher_round', '@drawable/sstp_switcher_logo').replace('@mipmap/ic_launcher', '@drawable/sstp_switcher_logo')
manifest.write_text(manifest_text, encoding="utf-8")
logo = root / "app/src/main/res/drawable/sstp_switcher_logo.xml"
logo.write_text("""<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp" android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#2F6EF2" android:pathData="M0,0h108v108h-108z"/>
    <path android:fillColor="#FFFFFF" android:pathData="M68,28c-4,-4 -10,-6 -17,-6 -13,0 -22,8 -22,19 0,10 7,15 20,18l7,2c7,2 10,4 10,8 0,5 -5,8 -12,8 -8,0 -15,-4 -20,-10l-9,10c7,9 17,14 29,14 16,0 27,-9 27,-22 0,-10 -7,-16 -21,-20l-8,-2c-6,-2 -8,-4 -8,-7 0,-4 4,-7 10,-7 5,0 10,2 14,6z"/>
    <path android:fillColor="#FFFFFF" android:pathData="M77,18l-4,12h8l-7,15 19,-20h-10l4,-7z"/>
</vector>
""", encoding="utf-8")
