# 0. Sync Native Modules & Reverse Port
echo "🔄  Syncing Native Modules..."
# npx expo prebuild --platform android --no-install # Optional: use if native code is out of sync

echo "🔀  Setting up ADB Reverse Port (8844)..."
adb reverse tcp:8844 tcp:8844
echo "🔀  Setting up ADB Reverse Port (8081 for Metro Bundler)..."
adb reverse tcp:8081 tcp:8081

# 1. Clean and Build
echo "🏗  Building APK..."
cd android
./gradlew assembleDebug

if [ $? -eq 0 ]; then
    echo "✅  Build Successful!"
    
    APK_PATH="app/build/outputs/apk/debug/app-debug.apk"
    
    # 2. Install via ADB
    echo "📲  Installing to device via ADB..."
    adb install -r $APK_PATH
    
    if [ $? -eq 0 ]; then
        echo "🚀  Installation Complete! Launching App..."
        # 3. Launch the App
        adb shell am start -n com.kiyotoka.mobilehud/.MainActivity
    else
        echo "❌  Installation failed. Is your phone connected via USB/ADB?"
    fi
else
    echo "❌  Build failed. Check the errors above."
fi
