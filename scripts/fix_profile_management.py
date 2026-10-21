from pathlib import Path

root = Path("upstream")
home_path = root / "app/src/main/java/kittoku/osc/fragment/HomeFragment.kt"
home = home_path.read_text(encoding="utf-8")

old_order = "order = entries.keys.indexOf(entry.key)"
new_order = 'order = prefs.getInt("PROFILE_FIELD.$name.ORDER", Int.MAX_VALUE)'
if home.count(old_order) != 1:
    raise SystemExit(f"Expected one profile-order assignment, found {home.count(old_order)}")
home = home.replace(old_order, new_order, 1)

old_rename = """                                listOf("HOST", "LOGIN", "PASSWORD", "ORDER", "STATUS").forEach { field ->
                                    val old = "PROFILE_FIELD.$name.$field"
                                    val value = prefs.getString(old, null)
                                    if (value != null) editor.putString("PROFILE_FIELD.$next.$field", value)
                                    editor.remove(old)
                                }"""
new_rename = """                                listOf("HOST", "LOGIN", "PASSWORD").forEach { field ->
                                    val old = "PROFILE_FIELD.$name.$field"
                                    val value = prefs.getString(old, null)
                                    if (value != null) editor.putString("PROFILE_FIELD.$next.$field", value)
                                    editor.remove(old)
                                }
                                listOf("ORDER", "STATUS").forEach { field ->
                                    val old = "PROFILE_FIELD.$name.$field"
                                    if (prefs.contains(old)) {
                                        editor.putInt("PROFILE_FIELD.$next.$field", prefs.getInt(old, 0))
                                    }
                                    editor.remove(old)
                                }"""
if home.count(old_rename) != 1:
    raise SystemExit(f"Expected one rename migration block, found {home.count(old_rename)}")
home = home.replace(old_rename, new_rename, 1)
home_path.write_text(home, encoding="utf-8")

layout_path = root / "app/src/main/res/layout/preference_saved_connection.xml"
layout = layout_path.read_text(encoding="utf-8")
old_row = """        <TextView
            android:id="@+id/saved_status_dot"
            android:layout_width="32dp"
            android:layout_height="32dp"
            android:gravity="center"
            android:text="●"
            android:textSize="23sp"
            android:textColor="#D64545" />"""
new_row = """        <TextView
            android:id="@+id/saved_manage_button"
            android:layout_width="40dp"
            android:layout_height="40dp"
            android:gravity="center"
            android:contentDescription="Управление подключением"
            android:text="⋮"
            android:textSize="26sp"
            android:textColor="#68758A"
            android:clickable="true"
            android:focusable="true" />
        <TextView
            android:id="@+id/saved_status_dot"
            android:layout_width="32dp"
            android:layout_height="32dp"
            android:gravity="center"
            android:text="●"
            android:textSize="23sp"
            android:textColor="#D64545" />"""
if layout.count(old_row) != 1:
    raise SystemExit(f"Expected one status-dot layout block, found {layout.count(old_row)}")
layout_path.write_text(layout.replace(old_row, new_row, 1), encoding="utf-8")

pref_path = root / "app/src/main/java/kittoku/osc/preference/custom/SavedConnectionPreference.kt"
pref = pref_path.read_text(encoding="utf-8")
old_bind = """        val dot = holder.findViewById(R.id.saved_status_dot) as TextView
        val titleView = holder.findViewById(android.R.id.title) as TextView"""
new_bind = """        val dot = holder.findViewById(R.id.saved_status_dot) as TextView
        val titleView = holder.findViewById(android.R.id.title) as TextView
        val manageButton = holder.findViewById(R.id.saved_manage_button) as TextView
        manageButton.setOnClickListener { onManage?.invoke() }"""
if pref.count(old_bind) != 1:
    raise SystemExit(f"Expected one card view-binding block, found {pref.count(old_bind)}")
pref = pref.replace(old_bind, new_bind, 1)
pref_path.write_text(pref, encoding="utf-8")

print("Fixed profile ordering, made rename/delete actions visible, and preserved typed order/status values on rename.")
