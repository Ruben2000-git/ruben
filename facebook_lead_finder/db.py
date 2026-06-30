"""
Общие функции для работы с базой данных SQLite.
Используется всеми остальными файлами (collector.py, filter.py, app.py).
"""

import sqlite3
import config


def get_connection():
    """Открыть соединение с базой данных."""
    conn = sqlite3.connect(config.DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создать таблицу постов, если она ещё не существует."""
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,        -- уникальный id поста (берём из ссылки на пост)
            group_name TEXT,
            post_url TEXT,
            author TEXT,
            text TEXT,
            posted_at TEXT,             -- время публикации поста (ISO формат)
            collected_at TEXT,          -- когда мы его нашли
            score INTEGER,
            job_type TEXT,
            location TEXT,
            job_size TEXT,
            red_flags TEXT,
            worth_it TEXT,
            draft_reply TEXT,
            analyzed INTEGER DEFAULT 0  -- 0 = ещё не отправлен в Claude, 1 = обработан
        )
        """
    )
    conn.commit()
    conn.close()


def post_exists(post_id):
    """Проверить, видели ли мы уже этот пост (защита от дубликатов)."""
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM posts WHERE id = ?", (post_id,)).fetchone()
    conn.close()
    return row is not None


def insert_post(post):
    """Сохранить новый пост в базу (ещё без анализа Claude)."""
    conn = get_connection()
    conn.execute(
        """
        INSERT OR IGNORE INTO posts
            (id, group_name, post_url, author, text, posted_at, collected_at, analyzed)
        VALUES (:id, :group_name, :post_url, :author, :text, :posted_at, :collected_at, 0)
        """,
        post,
    )
    conn.commit()
    conn.close()


def get_unanalyzed_posts():
    """Получить все посты, ещё не отправленные в Claude."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM posts WHERE analyzed = 0").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_analysis(post_id, analysis):
    """Записать результат анализа Claude для конкретного поста."""
    conn = get_connection()
    conn.execute(
        """
        UPDATE posts SET
            score = :score,
            job_type = :job_type,
            location = :location,
            job_size = :job_size,
            red_flags = :red_flags,
            worth_it = :worth_it,
            draft_reply = :draft_reply,
            analyzed = 1
        WHERE id = :id
        """,
        {**analysis, "id": post_id},
    )
    conn.commit()
    conn.close()


def get_all_leads(min_score=0):
    """Получить все проанализированные посты для дашборда, новые сверху."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM posts
        WHERE analyzed = 1 AND score >= ?
        ORDER BY collected_at DESC
        """,
        (min_score,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
