[app]
title = Hyper Star Jump
package.name = hyperstarjump
package.domain = org.hyperstarjump

source.dir = .
source.main = main.py
source.include_exts = py,png,jpg,kv,atlas,json,wav,ogg

version = 1.0

requirements = python3,pygame-ce

orientation = portrait
fullscreen = 1

android.archs = arm64-v8a
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.permissions = INTERNET

[buildozer]
log_level = 2
warn_on_root = 1
