# Rock — YouTube Live → M3U8

Плейлист рок-каналів з живих трансляцій YouTube. Є два способи користуватись.

## 1. Готовий плейлист з GitHub (нічого не треба запускати)

```
https://raw.githubusercontent.com/crux1974/Rock/main/streams.m3u8
```

GitHub Actions оновлює його кожні 3 години (і одразу після зміни `channels.txt`).
Ручний запуск: вкладка **Actions → Update IPTV Playlist → Run workflow**.

⚠️ Посилання YouTube прив'язані до IP, з якого їх отримали (тут — сервер GitHub).
Деякі плеєри через це отримують помилку 403. Якщо так — використовуйте спосіб 2.

## 2. Власний сервер (найнадійніше)

Запускайте в тій самій мережі, що й телевізор (ПК, NAS, Raspberry Pi з Docker):

```
git clone https://github.com/crux1974/Rock && cd Rock
docker compose up -d --build
```

У плеєрі (TiviMate, OTT Navigator, VLC, Kodi…) додайте:

```
http://IP_СЕРВЕРА:10000/playlist.m3u8
```

Сервер при кожному відкритті каналу дає свіже посилання — нічого не «протухає».
Стан каналів: `http://IP_СЕРВЕРА:10000/`. Без Docker: `pip install -r requirements.txt && python app.py`
(потрібен ще [Deno](https://deno.com)).

## Якість

За замовчуванням для кожного каналу береться **найвища доступна якість** (зі звуком) —
плеєр одразу грає її і не перемикається на нижчу. Файли з якістю лежать у папці `channels/`.
Щоб повернути автоматичний вибір якості плеєром, задайте змінну `BEST_QUALITY=0`
(у workflow — у кроці «Generate playlist», для сервера — у `docker-compose.yml`).

## Як додати канал

Відредагуйте `channels.txt` (можна прямо на сайті GitHub):

```
Назва каналу | https://www.youtube.com/@Канал/live | Rock
```

Посилання `@Канал/live` краще, ніж `watch?v=…`: воно завжди веде на поточний ефір.

## Якщо YouTube пише «Sign in to confirm you're not a bot»

Експортуйте cookies (розширення «Get cookies.txt LOCALLY», краще з окремого акаунта) і:

- для GitHub Actions: **Settings → Secrets and variables → Actions → New secret**,
  назва `YT_COOKIES`, значення — весь вміст файлу;
- для власного сервера: покладіть `cookies.txt` поруч і розкоментуйте рядок у `docker-compose.yml`.

**Ніколи не додавайте cookies.txt у репозиторій** — це доступ до вашого акаунта.
