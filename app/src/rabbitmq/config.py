from __future__ import annotations

import os


def get_rabbitmq_dsn() -> dict:
    """
    Собираем параметры подключения из env

    """

    return {
        "host": os.getenv("RABBITMQ_HOST", "rabbitmq"),
        "port": int(os.getenv("RABBITMQ_PORT", "5672")),
        "user": os.getenv("RABBITMQ_DEFAULT_USER", "guest"),
        "password": os.getenv("RABBITMQ_DEFAULT_PASS", "guest"),
        "vhost": os.getenv("RABBITMQ_VHOST", "/"),
        "queue": os.getenv("RABBITMQ_QUEUE", "ml_task_queue"),
    }





