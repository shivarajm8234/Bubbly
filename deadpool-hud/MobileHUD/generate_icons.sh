#!/bin/bash
LOGO="/home/kiyotoka/Dashy/deadpool_logo.png"
RES_DIR="/home/kiyotoka/Dashy/MobileHUD/android/app/src/main/res"

# mipmap dimensions
declare -A sizes=(
  ["mdpi"]=48
  ["hdpi"]=72
  ["xhdpi"]=96
  ["xxhdpi"]=144
  ["xxxhdpi"]=192
)

for dpi in "${!sizes[@]}"; do
  size=${sizes[$dpi]}
  dir="$RES_DIR/mipmap-$dpi"
  mkdir -p "$dir"
  
  convert "$LOGO" -resize ${size}x${size} "$dir/ic_launcher.webp"
  convert "$LOGO" -resize ${size}x${size} "$dir/ic_launcher_round.webp"
  convert "$LOGO" -resize ${size}x${size} "$dir/ic_launcher_foreground.webp"
done
