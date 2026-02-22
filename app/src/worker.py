from __future__ import annotations

import json
import logging
import os
import time
from decimal import Decimal
from typing import Any
from uuid import UUID

import pika

from .db.enums import PredictionStatus
from .db.session import make_engine, session_scope
from .repositories.billing import BillingRepository
from .repositories.history import PredictionHistoryRepository
from .repositories.ml_models import MLModelRepository
from .rabbitmq.config import get_rabbitmq_dsn


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ml-worker")


def _validate_features(features: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:

    rows: list[Any]
    if isinstance(features, dict) and "rows" in features:
        rows = features.get("rows")
    else:
        rows = [features]

    valid: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            errors.append({"row_index": i, "field": "row", "message": "row must be an object"})
            continue
        if not r:
            errors.append({"row_index": i, "field": "row", "message": "row must not be empty"})
            continue
        if not all(isinstance(k, str) for k in r.keys()):
            errors.append({"row_index": i, "field": "row", "message": "all keys must be strings"})
            continue
        valid.append(r)

    return valid, errors


def _predict_mock(row: dict[str, Any]) -> float:
    return float(abs(hash(str(sorted(row.items())))) % 1000) / 1000.0


def _process_task(payload: dict[str, Any], worker_id: str) -> None:
    task_id = UUID(payload["task_id"])
    user_id = UUID(payload["user_id"])
    model_name = payload["model"]["name"]
    model_version = payload["model"]["version"]
    features = payload.get("features")

    engine = make_engine(echo=False)
    models = MLModelRepository()
    history = PredictionHistoryRepository()
    billing = BillingRepository()

    with session_scope(engine) as session:
        item = history.get(session, task_id)
        if item is None:
            logger.warning("Task %s not found in DB; ack anyway", task_id)
            return

        model = models.get_by_name_version(session, name=model_name, version=model_version)
        if model is None or not model.is_active:
            item.status = PredictionStatus.FAILED
            item.errors = [{"row_index": 0, "field": "model", "message": "Model not found or disabled"}]
            history.save(session, item)
            return

        valid_rows, errors = _validate_features(features)
        predictions: list[dict[str, Any]] = []
        for row in valid_rows:
            predictions.append({"prediction": _predict_mock(row), "worker_id": worker_id, "status": "success"})

        item.valid_rows = len(valid_rows)
        item.invalid_rows = len(errors)
        item.errors = errors
        item.valid_data = valid_rows
        item.predictions = predictions

        item.charged = Decimal("0")
        item.status = PredictionStatus.FAILED

        if item.valid_rows > 0:
            charged = Decimal(model.price_per_row) * Decimal(item.valid_rows)
            try:
                billing.charge(session, user_id, charged)
                item.charged = charged
                item.status = PredictionStatus.APPLIED
            except RuntimeError:
                item.status = PredictionStatus.FAILED
                item.errors = item.errors + [
                    {"row_index": 0, "field": "billing", "message": "Not enough credits"}
                ]

        history.save(session, item)


def _connect_with_retries(connection_params: pika.ConnectionParameters) -> pika.BlockingConnection:
    max_retries = int(os.getenv("RABBITMQ_CONNECT_RETRIES", "60"))
    sleep_seconds = float(os.getenv("RABBITMQ_CONNECT_SLEEP", "1.0"))

    for attempt in range(1, max_retries + 1):
        try:
            return pika.BlockingConnection(connection_params)
        except pika.exceptions.AMQPConnectionError as e:
            logger.warning(
                "RabbitMQ is not ready yet (attempt %s/%s): %s",
                attempt,
                max_retries,
                repr(e),
            )
            time.sleep(sleep_seconds)

    raise RuntimeError("RabbitMQ is not available after retries")


def main() -> None:
    cfg = get_rabbitmq_dsn()
    worker_id = os.getenv("WORKER_ID", "worker")

    connection_params = pika.ConnectionParameters(
        host=cfg["host"],
        port=cfg["port"],
        virtual_host=cfg["vhost"],
        credentials=pika.PlainCredentials(username=cfg["user"], password=cfg["password"]),
        heartbeat=30,
        blocked_connection_timeout=2,
    )

    connection = _connect_with_retries(connection_params)
    channel = connection.channel()
    channel.queue_declare(queue=cfg["queue"], durable=True)


    channel.basic_qos(prefetch_count=1)

    def callback(ch, method, properties, body):
        try:
            payload = json.loads(body.decode("utf-8"))
            time.sleep(float(os.getenv("WORKER_SLEEP", "0")))
            _process_task(payload, worker_id=worker_id)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:
            logger.exception("Failed to process message")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    channel.basic_consume(queue=cfg["queue"], on_message_callback=callback, auto_ack=False)
    logger.info("[%s] Waiting for messages in queue=%s", worker_id, cfg["queue"])
    channel.start_consuming()


if __name__ == "__main__":
    main()


