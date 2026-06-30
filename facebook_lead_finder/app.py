"""
app.py

Flask-дашборд, доступный на localhost. Показывает все найденные лиды
карточками, отсортированными по новизне, с цветовой индикацией score,
кнопкой "Copy" для черновика ответа и кнопкой "Refresh Now" для запуска
сбора+анализа прямо из браузера.
"""

import logging
import threading

from flask import Flask, jsonify, render_template_string, request

import collector
import config
import db
import filter as lead_filter

app = Flask(__name__)
logger = logging.getLogger("facebookleads")

PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Facebook Leads - Handyman</title>
<style>
  body { font-family: -apple-system, Arial, sans-serif; background: #f2f2f5; margin: 0; padding: 12px; }
  h1 { font-size: 20px; text-align: center; }
  .toolbar { display: flex; justify-content: center; gap: 10px; margin-bottom: 16px; }
  button { padding: 10px 16px; border: none; border-radius: 8px; font-size: 14px; cursor: pointer; }
  .refresh-btn { background: #1877f2; color: white; }
  .copy-btn { background: #444; color: white; margin-top: 8px; }
  .card { background: white; border-radius: 10px; padding: 14px; margin-bottom: 12px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.15); border-left: 6px solid #ccc; }
  .score-high { border-left-color: #2ecc71; }
  .score-mid  { border-left-color: #f39c12; }
  .score-low  { border-left-color: #e74c3c; }
  .meta { font-size: 12px; color: #666; margin-bottom: 6px; }
  .text { font-size: 14px; margin-bottom: 8px; white-space: pre-wrap; }
  .badge { display: inline-block; background: #eee; border-radius: 6px; padding: 2px 8px;
           font-size: 12px; margin-right: 6px; }
  .reply { background: #f7f7f7; border-radius: 8px; padding: 8px; font-size: 13px; white-space: pre-wrap; }
  .status { text-align: center; font-size: 13px; color: #777; margin-bottom: 10px; }
</style>
</head>
<body>
<h1>Facebook Leads - Buffalo NY</h1>
<div class="toolbar">
  <button class="refresh-btn" onclick="refreshNow()">Refresh Now</button>
</div>
<div class="status" id="status"></div>
<div id="leads">
{% for lead in leads %}
  <div class="card {{ 'score-high' if lead.score >= 7 else ('score-mid' if lead.score >= 4 else 'score-low') }}">
    <div class="meta">{{ lead.group_name }} - {{ lead.posted_at }}</div>
    <div>
      <span class="badge">Score: {{ lead.score }}</span>
      <span class="badge">{{ lead.job_type }}</span>
      <span class="badge">{{ lead.job_size }}</span>
      <span class="badge">{{ lead.worth_it }}</span>
    </div>
    <div class="text">{{ lead.text }}</div>
    {% if lead.red_flags and lead.red_flags != 'none' %}
      <div class="meta">⚠ {{ lead.red_flags }}</div>
    {% endif %}
    <div class="reply" id="reply-{{ lead.id }}">{{ lead.draft_reply }}</div>
    <button class="copy-btn" onclick="copyReply('{{ lead.id }}')">Copy</button>
    <div class="meta"><a href="{{ lead.post_url }}" target="_blank">Открыть пост</a></div>
  </div>
{% else %}
  <p style="text-align:center;color:#888;">Лидов пока нет. Нажмите Refresh Now.</p>
{% endfor %}
</div>

<script>
function copyReply(id) {
    const text = document.getElementById('reply-' + id).innerText;
    navigator.clipboard.writeText(text);
}

function refreshNow() {
    document.getElementById('status').innerText = 'Сбор и анализ... это может занять пару минут';
    fetch('/refresh', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            document.getElementById('status').innerText =
                'Готово: новых постов ' + data.new_posts + ', проанализировано ' + data.analyzed;
            location.reload();
        })
        .catch(() => {
            document.getElementById('status').innerText = 'Ошибка при обновлении, смотрите facebookleads.log';
        });
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    leads = db.get_all_leads(min_score=0)
    return render_template_string(PAGE_TEMPLATE, leads=leads)


@app.route("/refresh", methods=["POST"])
def refresh():
    """Запустить сбор новых постов и их анализ, вернуть короткую сводку."""
    try:
        new_posts = collector.run_collection() or 0
        analyzed = lead_filter.run_filtering() or 0
        return jsonify({"new_posts": new_posts, "analyzed": analyzed})
    except Exception as e:
        logger.error("Ошибка при ручном обновлении: %s", e)
        return jsonify({"error": str(e)}), 500


def run_app():
    db.init_db()
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=False)


if __name__ == "__main__":
    run_app()
