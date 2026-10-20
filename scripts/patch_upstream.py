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
print("Patched Russian UI and automatic saved-profile switching.")

# Single-page modern UI. Keep the upstream VPN engine and profile serialization unchanged.
text = text.replace("import android.widget.Toast\\n", """import android.widget.Toast
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
""")
text = replace_once(text,
    "    private lateinit var settingFragment: PreferenceFragmentCompat\\n",
    "    private lateinit var settingFragment: PreferenceFragmentCompat\\n    private lateinit var profileList: LinearLayout\\n    private lateinit var statusLabel: TextView\\n",
    "modern UI fields")
text = replace_once(text, "    private fun updatePreferenceView() {", """
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
            card.addView(uiText("Подключить  ›", 13f, Color.rgb(42,103,230), true))
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
            setPadding(dp(16),dp(16),dp(16),dp(16)); setOnClickListener { showSaveDialog() }
        })
        setContentView(page)
        refreshProfiles()
""", "replace tabbed home screen")
text = text.replace('Toast.makeText(this, "PROFILE SAVED", Toast.LENGTH_SHORT).show()', 'refreshProfiles()\\n                Toast.makeText(this, "Подключение сохранено", Toast.LENGTH_SHORT).show()')
text = text.replace('Toast.makeText(this, "PROFILE IMPORTED", Toast.LENGTH_SHORT).show()', 'refreshProfiles()\\n                Toast.makeText(this, "Профиль импортирован", Toast.LENGTH_SHORT).show()')
activity.write_text(text, encoding="utf-8")
print("Modern single-page profile list applied.")
