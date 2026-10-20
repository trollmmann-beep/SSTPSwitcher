# SSTP Switcher for Android

Android SSTP VPN client based on [Open-SSTP-Client](https://github.com/kittoku/Open-SSTP-Client) (MIT license).

## Build APK

Open **Actions → Build SSTP Switcher APK** in this repository. The workflow checks out the upstream SSTP engine, applies the app branding/profile-switch patch, builds a debug APK, and publishes it as the **SSTPSwitcher-APK** artifact.

Artifact download page: https://github.com/trollmmann-beep/SSTPSwitcher/actions

## Use

1. Install the APK on Android.
2. Open the app and configure Host, Username and Password for the first router. Host should be the hostname only, without a port; configure the SSTP port in Settings if required.
3. Use the app menu to save the profile. Repeat for each router, giving each profile a distinct name. The app stores profiles locally on the device.
4. Open the app menu's profile selector, choose the router, and the app disconnects the previous session (if active), loads the selected profile, then requests/starts the VPN connection.
5. The underlying client shows its connection state in the app/Android VPN status icon.

## Compatibility note

Open-SSTP-Client was developed primarily for VPN Azure/SoftEther. Its upstream documentation says it has not been tested against all other SSTP servers. Keenetic SSTP compatibility must be tested on the actual routers; a successful APK build alone does not prove a successful connection.

Passwords and saved profile data are stored by the upstream app in Android app-private preferences. Treat the phone as sensitive equipment.

## License

The upstream SSTP engine is MIT-licensed. This repository's patch/workflow is provided for building the app; see upstream license and notices in the upstream repository.
