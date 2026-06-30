"""
filter.py

Берёт все ещё необработанные посты из базы данных и отправляет каждый
по очереди в Claude API, чтобы получить оценку лида и черновик ответа.
Обрабатывает ТОЛЬКО новые посты (analyzed = 0), чтобы не тратить запросы зря.
"""

import json
import logging

import anthropic

import config
import db

logger = logging.getLogger("facebookleads")

SYSTEM_PROMPT = f"""You are an assistant that screens Facebook Marketplace / \
Buy-and-Sell group posts for a handyman/contractor business in Buffalo, NY. \
The contractor's name is {config.CONTRACTOR_NAME} and the business handles: \
{config.BUSINESS_DESCRIPTION}.

For the given post, respond with STRICT JSON only (no markdown, no extra text), \
using exactly this schema:

{{
  "score": <integer 0-10, how good a lead this is for the contractor>,
  "job_type": "<short job category, e.g. 'gutter repair'>",
  "location": "<location mentioned in the post, or 'unknown'>",
  "job_size": "<'small' | 'medium' | 'large'>",
  "red_flags": "<short note on anything suspicious/lowball/out of scope, or 'none'>",
  "worth_it": "<'yes' | 'no' | 'maybe'>",
  "draft_reply": "<a short friendly reply starting with 'Hi! I'm {config.CONTRACTOR_NAME}, a contractor...', no price mentioned, asking exactly one clarifying question>"
}}

Only return the JSON object, nothing else.
"""


def get_client():
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY не задан. Установите переменную окружения.")
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def analyze_post(client, post_text):
    """Отправить текст поста в Claude и получить разобранный JSON-результат."""
    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": post_text}],
    )

    raw_text = response.content[0].text.strip()

    # На случай, если модель всё-таки обернёт ответ в markdown-блок ```json ... ```
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.replace("json\n", "", 1)

    data = json.loads(raw_text)
    return data


def run_filtering():
    """Главная функция: проанализировать все необработанные посты."""
    db.init_db()
    posts = db.get_unanalyzed_posts()

    if not posts:
        logger.info("Нет новых постов для анализа Claude.")
        return 0

    client = get_client()
    analyzed_count = 0

    for post in posts:
        try:
            analysis = analyze_post(client, post["text"])
            analysis["id"] = post["id"]
            db.save_analysis(post["id"], analysis)
            analyzed_count += 1
            logger.info(
                "Пост %s проанализирован: score=%s, worth_it=%s",
                post["id"],
                analysis.get("score"),
                analysis.get("worth_it"),
            )
        except Exception as e:
            logger.error("Ошибка анализа поста %s: %s", post["id"], e)
            continue

    logger.info("Анализ завершён. Обработано постов: %d", analyzed_count)
    return analyzed_count


if __name__ == "__main__":
    logging.basicConfig(
        filename=config.LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    run_filtering()
