"""
collector.py

Заходит в Facebook под вашим личным аккаунтом (через Playwright, как обычный
браузер) и читает ленту групп, в которых вы СОСТОИТЕ. Ищет посты с нужными
ключевыми словами, отбрасывает посты старше MAX_POST_AGE_HOURS и сохраняет
новые (ещё не виденные) посты в базу данных SQLite.

ВАЖНО: это не использует официальный Graph API Facebook (он не даёт доступа
к постам в группах для сторонних приложений). Это автоматизация обычного
браузера под вашим же логином - технически нарушает Условия использования
Facebook, поэтому используйте на свой риск (см. README.md).
"""

import logging
import re
import time
from datetime import datetime, timedelta

from playwright.sync_api import sync_playwright

import config
import db

logger = logging.getLogger("facebookleads")


def setup_logging():
    logging.basicConfig(
        filename=config.LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    # Дублируем в консоль, чтобы было видно прогресс при ручном запуске.
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger("facebookleads").addHandler(console)


def post_matches_keywords(text):
    """Проверить, упоминает ли текст поста хотя бы одно ключевое слово."""
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in config.KEYWORDS)


def parse_relative_time(label):
    """
    Facebook показывает время поста как "2h", "3 hrs", "Yesterday at 9:00 PM",
    "5d" и т.д. Это грубый разбор самых частых форматов - достаточно для
    решения "старше 48 часов или нет". Если не получилось распознать формат,
    считаем пост свежим (лучше показать лишний пост, чем пропустить лид).
    """
    if not label:
        return datetime.now()

    label = label.strip().lower()

    match = re.match(r"(\d+)\s*m(in)?\b", label)
    if match:
        return datetime.now() - timedelta(minutes=int(match.group(1)))

    match = re.match(r"(\d+)\s*h(r|rs)?\b", label)
    if match:
        return datetime.now() - timedelta(hours=int(match.group(1)))

    match = re.match(r"(\d+)\s*d\b", label)
    if match:
        return datetime.now() - timedelta(days=int(match.group(1)))

    if "yesterday" in label:
        return datetime.now() - timedelta(days=1)

    # Не распознали формат - считаем свежим, чтобы не потерять лид.
    return datetime.now()


def login_and_get_context(playwright):
    """
    Открыть браузер и войти в Facebook.
    При первом запуске (нет сохранённой сессии) откроет окно, чтобы вы
    вручную ввели логин/2FA - после этого сессия сохранится в файл и
    следующие запуски будут проходить автоматически.
    """
    browser = playwright.chromium.launch(headless=config.HEADLESS)

    import os

    if os.path.exists(config.BROWSER_STATE_FILE):
        context = browser.new_context(storage_state=config.BROWSER_STATE_FILE)
        logger.info("Использую сохранённую сессию Facebook.")
        return browser, context

    # Сессии нет - логинимся вручную.
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.facebook.com/login")

    if config.FB_EMAIL and config.FB_PASSWORD:
        page.fill("#email", config.FB_EMAIL)
        page.fill("#pass", config.FB_PASSWORD)
        page.click('button[name="login"]')

    logger.info(
        "Если появилась проверка безопасности (2FA/капча) - пройдите её "
        "вручную в открывшемся окне браузера. У вас есть 90 секунд."
    )
    page.wait_for_timeout(90_000)

    context.storage_state(path=config.BROWSER_STATE_FILE)
    logger.info("Сессия Facebook сохранена в %s", config.BROWSER_STATE_FILE)
    page.close()
    return browser, context


def collect_group_posts(page, group_url, group_name):
    """Прокрутить ленту одной группы и собрать подходящие посты."""
    found = []

    page.goto(group_url)
    page.wait_for_timeout(6000)
    try:
        page.wait_for_selector('div[role="article"]', timeout=15000)
    except Exception:
        logger.warning("Группа '%s': лента не появилась за 15 секунд", group_name)

    # Прокручиваем страницу несколько раз, чтобы подгрузились новые посты.
    # Facebook подгружает посты постепенно при скролле, поэтому делаем
    # больше итераций с более длинными паузами, чем для обычных сайтов.
    for _ in range(15):
        page.mouse.wheel(0, 2500)
        page.wait_for_timeout(2500)

    # Facebook часто меняет вёрстку, поэтому ищем посты максимально широко:
    # каждый блок поста обычно содержит role="article".
    articles = page.query_selector_all('div[role="article"]')
    logger.info("Группа '%s': найдено %d блоков постов на странице", group_name, len(articles))

    for article in articles:
        try:
            text_el = article.query_selector('div[data-ad-preview="message"]')
            text = text_el.inner_text() if text_el else article.inner_text()
            if not text or not post_matches_keywords(text):
                continue

            link_el = article.query_selector('a[href*="/posts/"], a[href*="/permalink/"]')
            post_url = link_el.get_attribute("href") if link_el else group_url
            post_id = re.sub(r"\D", "", post_url) or str(hash(text))
            post_id = f"{group_name}_{post_id}"

            time_el = article.query_selector("a[aria-label] abbr, a abbr")
            time_label = time_el.get_attribute("aria-label") if time_el else None
            posted_at = parse_relative_time(time_label)

            if posted_at < datetime.now() - timedelta(hours=config.MAX_POST_AGE_HOURS):
                continue

            author_el = article.query_selector("h2, h3")
            author = author_el.inner_text() if author_el else "Unknown"

            found.append(
                {
                    "id": post_id,
                    "group_name": group_name,
                    "post_url": post_url,
                    "author": author,
                    "text": text.strip()[:3000],
                    "posted_at": posted_at.isoformat(),
                    "collected_at": datetime.now().isoformat(),
                }
            )
        except Exception as e:
            logger.warning("Не удалось разобрать один из постов: %s", e)
            continue

    return found


def run_collection():
    """Главная функция: пройтись по всем группам и сохранить новые лиды."""
    setup_logging()
    db.init_db()

    if not config.FACEBOOK_GROUPS:
        logger.warning("Список FACEBOOK_GROUPS в config.py пуст - нечего собирать.")
        return

    new_count = 0

    with sync_playwright() as playwright:
        browser, context = login_and_get_context(playwright)
        page = context.new_page()

        for group_url in config.FACEBOOK_GROUPS:
            group_name = group_url.rstrip("/").split("/")[-1]
            try:
                posts = collect_group_posts(page, group_url, group_name)
            except Exception as e:
                logger.error("Ошибка при сборе группы %s: %s", group_url, e)
                continue

            for post in posts:
                if db.post_exists(post["id"]):
                    continue
                db.insert_post(post)
                new_count += 1
                logger.info("Новый пост сохранён: %s", post["post_url"])

            time.sleep(3)  # небольшая пауза между группами, чтобы вести себя как человек

        context.close()
        browser.close()

    logger.info("Сбор завершён. Новых постов: %d", new_count)
    return new_count


if __name__ == "__main__":
    run_collection()
