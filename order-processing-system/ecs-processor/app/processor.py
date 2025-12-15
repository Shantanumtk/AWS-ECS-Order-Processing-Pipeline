import logging
import random
import time
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class OrderProcessor:
    def update_order_status(self, conn, order_id: str, status: str, message: str = None):
        with conn.cursor() as cur:
            cur.execute("UPDATE orders SET status = %s, updated_at = %s WHERE id = %s", (status, datetime.utcnow(), order_id))
            cur.execute(
                "INSERT INTO order_status_log (id, order_id, status, message, created_at) VALUES (%s, %s, %s, %s, %s)",
                (str(uuid.uuid4()), order_id, status, message, datetime.utcnow())
            )
        logger.info(f"Order {order_id} status updated to {status}")

    def process_payment(self, conn, order_id: str, amount: float) -> bool:
        logger.info(f"Processing payment of ${amount:.2f} for order {order_id}")
        time.sleep(2)
        success = random.random() < 0.95
        if success:
            logger.info(f"Payment successful for order {order_id}")
        else:
            logger.warning(f"Payment failed for order {order_id}")
        return success

    def fulfill_order(self, conn, order_id: str):
        logger.info(f"Fulfilling order {order_id}")
        time.sleep(1)
        with conn.cursor() as cur:
            cur.execute("SELECT product_name, quantity FROM order_items WHERE order_id = %s", (order_id,))
            items = cur.fetchall()
            for item in items:
                logger.info(f"Fulfilling: {item['quantity']}x {item['product_name']}")
        logger.info(f"Order {order_id} fulfilled successfully")

    def cancel_order(self, conn, order_id: str, reason: str = None):
        logger.info(f"Cancelling order {order_id}")
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM orders WHERE id = %s", (order_id,))
            result = cur.fetchone()
            if not result:
                raise ValueError(f"Order {order_id} not found")
            if result['status'] in ['FULFILLED', 'COMPLETED', 'CANCELLED']:
                raise ValueError(f"Cannot cancel order with status {result['status']}")
        self.update_order_status(conn, order_id, "CANCELLED", reason or "Order cancelled")
        logger.info(f"Order {order_id} cancelled successfully")
