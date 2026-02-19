from __future__ import annotations

import json
from typing import Any

import pika

from .config import get_rabbitmq_dsn


def _connection_params() -> pika.ConnectionParameters:
    cfg = get_rabbitmq_dsn()
    return pika.ConnectionParameters(
        host=cfg["host"],
        port=cfg["port"],
        virtual_host=cfg["vhost"],
        credentials=pika.PlainCredentials(username=cfg["user"], password=cfg["password"]),
        heartbeat=30,
        blocked_connection_timeout=2,
    )


def publish_task(payload: dict[str, Any]) -> None:
    """Публикует задачу в очередь RabbitMQ (default exchange)"""
    cfg = get_rabbitmq_dsn()
    connection = pika.BlockingConnection(_connection_params())
    channel = connection.channel()
    channel.queue_declare(queue=cfg["queue"], durable=True)

    channel.basic_publish(
        exchange="",
        routing_key=cfg["queue"],
        body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
        ),
    )
    connection.close()



