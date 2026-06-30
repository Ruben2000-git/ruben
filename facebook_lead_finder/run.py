"""
run.py

Единая точка входа: запускает Flask-дашборд и в фоне, каждые
SCAN_INTERVAL_MINUTES минут, выполняет сбор новых постов и их анализ.

Просто запустите: python run.py
"""

import logging
import threading
import time

import app as flask_app
import collector
import config
import db
import filter as lead_filter

logger = logging.getLogger("facebookleads")


def setup_logging():
    logging.basicConfig(
        filename=config.LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    fb_logger = logging.getLogger("facebookleads")
    if not fb_logger.handlers:
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        fb_logger.addHandler(console)


def scan_cycle():
    """Один полный цикл: собрать новые посты и проанализировать их."""
    logger.info("=== Запуск цикла сбора лидов ===")
    try:
        new_posts = collector.run_collection() or 0
        analyzed = lead_filter.run_filtering() or 0
        logger.info("Цикл завершён: новых постов %d, проанализировано %d", new_posts, analyzed)
    except Exception as e:
        logger.error("Ошибка в цикле сбора: %s", e)


def background_scheduler():
    """Бесконечный цикл: запускает scan_cycle каждые N минут."""
    while True:
        scan_cycle()
        time.sleep(config.SCAN_INTERVAL_MINUTES * 60)


def main():
    setup_logging()
    db.init_db()

    logger.info(
        "Запуск Facebook Lead Finder. Дашборд: http://%s:%d  (интервал сканирования: %d мин)",
        config.FLASK_HOST,
        config.FLASK_PORT,
        config.SCAN_INTERVAL_MINUTES,
    )

    scheduler_thread = threading.Thread(target=background_scheduler, daemon=True)
    scheduler_thread.start()

    flask_app.run_app()


if __name__ == "__main__":
    main()
