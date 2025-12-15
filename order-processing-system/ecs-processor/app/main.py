import json
import logging
import os
import signal
import time

import boto3
import psycopg2
from psycopg2.extras import RealDictCursor

from processor import OrderProcessor
from notifier import SNSNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DB_HOST = os.environ.get("DB_HOST")
DB_NAME = os.environ.get("DB_NAME")
DB_USERNAME = os.environ.get("DB_USERNAME")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

sqs_client = boto3.client("sqs", region_name=AWS_REGION)
running = True


def signal_handler(signum, frame):
    global running
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    running = False


def get_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USERNAME, password=DB_PASSWORD, cursor_factory=RealDictCursor)


def poll_sqs():
    try:
        response = sqs_client.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20,
            MessageAttributeNames=["All"]
        )
        return response.get("Messages", [])
    except Exception as e:
        logger.error(f"Error polling SQS: {e}")
        return []


def delete_message(receipt_handle: str):
    try:
        sqs_client.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)
        logger.info("Message deleted from SQS")
    except Exception as e:
        logger.error(f"Error deleting message from SQS: {e}")


def process_message(message: dict, processor: OrderProcessor, notifier: SNSNotifier):
    try:
        body = json.loads(message["Body"])
        order_id = body.get("order_id")

        if not order_id:
            logger.error("Message missing order_id")
            return False

        logger.info(f"Processing order: {order_id}")
        conn = get_db_connection()

        try:
            processor.update_order_status(conn, order_id, "PROCESSING", "Order processing started")
            notifier.send_notification(order_id, "PROCESSING", f"Order {order_id} is now being processed")

            logger.info(f"Processing payment for order {order_id}")
            payment_success = processor.process_payment(conn, order_id, body.get("total_amount", 0))

            if payment_success:
                processor.update_order_status(conn, order_id, "PAYMENT_CONFIRMED", "Payment processed successfully")
                notifier.send_notification(order_id, "PAYMENT_CONFIRMED", f"Payment confirmed for order {order_id}")

                logger.info(f"Fulfilling order {order_id}")
                processor.fulfill_order(conn, order_id)
                processor.update_order_status(conn, order_id, "FULFILLED", "Order has been fulfilled")
                notifier.send_notification(order_id, "FULFILLED", f"Order {order_id} has been fulfilled!")

                processor.update_order_status(conn, order_id, "COMPLETED", "Order completed successfully")
                notifier.send_notification(order_id, "COMPLETED", f"Order {order_id} completed. Thank you!")
            else:
                processor.update_order_status(conn, order_id, "PAYMENT_FAILED", "Payment processing failed")
                notifier.send_notification(order_id, "PAYMENT_FAILED", f"Payment failed for order {order_id}")
                return False

            conn.commit()
            logger.info(f"Successfully processed order: {order_id}")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Error processing order {order_id}: {e}")
            processor.update_order_status(conn, order_id, "FAILED", str(e))
            notifier.send_notification(order_id, "FAILED", f"Order {order_id} failed: {str(e)}")
            conn.commit()
            return False
        finally:
            conn.close()

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in message: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error processing message: {e}")
        return False


def main():
    global running

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Order Processor started")
    logger.info(f"SQS Queue URL: {SQS_QUEUE_URL}")
    logger.info(f"SNS Topic ARN: {SNS_TOPIC_ARN}")

    processor = OrderProcessor()
    notifier = SNSNotifier(SNS_TOPIC_ARN, AWS_REGION)

    while running:
        try:
            messages = poll_sqs()

            if not messages:
                logger.debug("No messages received, continuing to poll...")
                continue

            logger.info(f"Received {len(messages)} message(s)")

            for message in messages:
                if not running:
                    break

                success = process_message(message, processor, notifier)

                if success:
                    delete_message(message["ReceiptHandle"])
                else:
                    logger.warning("Message processing failed, will retry")

        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            if running:
                time.sleep(5)

    logger.info("Order Processor shutting down gracefully")


if __name__ == "__main__":
    main()
