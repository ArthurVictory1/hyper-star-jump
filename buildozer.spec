[app]

# (добавьте эту строку)
source.dir = .

# Название игры
title = Hyper Star Jump

# Имя пакета
package.name = hyperstarjump

# Домен пакета
package.domain = org.hyperstarjump

# Путь к исходным файлам игры (где лежит main.py)
source.include_exts = py,png,jpg,kv,atlas,json,wav,ogg

# Главный файл запуска
source.main = main.py

# Версия приложения
version = 1.0

# Необходимые библиотеки (обязательно python3 и pygame)
requirements = python3,pygame-ce
android.archs = arm64-v8a

# Поддерживаемая ориентация экрана (только портретная для аркады)
orientation = portrait

# Права приложения (доступ к интернету или хранилищу, если нужно)
# android.permissions = INTERNET

# Настройки для Android
android.api = 33
android.minAPI = 21
android.sdk = 30
android.ndk = 25b
android.accept_sdk_license = True
