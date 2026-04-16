#!/bin/bash
LOGO="/home/kiyotoka/Dashy/deadpool_logo.png"
RES_DIR="/home/kiyotoka/Dashy/MobileHUD/android/app/src/main/res"

# splash dimensions
declare -A sizes=(
  ["mdpi"]=288
  ["hdpi"]=432
  ["xhdpi"]=576
  ["xxhdpi"]=864
  ["xxxhdpi"]=1152
)

for dpi in "${!sizes[@]}"; do
  size=${sizes[$dpi]}
  dir="$RES_DIR/drawable-$dpi"
  mkdir -p "$dir"
  
  convert "$LOGO" -resize ${size}x${size} "$dir/splashscreen_logo.png"
done

cp "$LOGO" "/home/kiyotoka/Dashy/MobileHUD/assets/splash-icon.png"
