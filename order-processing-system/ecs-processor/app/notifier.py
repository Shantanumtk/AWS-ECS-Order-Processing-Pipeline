import json
import logging
from datetime import datetime
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SNSNotifier:
    def __init__(self, topic_arn: str, region: str = "us-east-1"):
        self.topic_arn = topic_arn
        self.sns_client = boto3.client("sns", region_name=region)

    def send_notification(self, order_id: str, event_type: str, message: str, attributes: Optional[dict] = None) -> bool:
        try:
            payload = {
                "order_id": order_id,
                "event_type": event_type,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "attributes": attributes or {}
            }

            message_attributes = {
                "event_type": {"DataType": "String", "StringValue": event_type},
                "order_id": {"DataType": "String", "StringValue": order_id}
            }

            subject = self._get_subject(event_type, order_id)

            response = self.sns_client.publish(
                TopicArn=self.topic_arn,
                Message=json.dumps(payload, default=str),
                Subject=subject,
                MessageAttributes=message_attributes
            )

            logger.info(f"SNS notification sent: {event_type} for order {order_id} (MessageId: {response.get('MessageId')})")
            return True

        except ClientError as e:
            logger.error(f"Failed to send SNS notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending SNS notification: {e}")
            return False

    def _get_subject(self, event_type: str, order_id: str) -> str:
        subjects = {
            "ORDER_CREATED": f"Order Received - {order_id[:8]}",
            "PROCESSING": f"Order Processing - {order_id[:8]}",
            "PAYMENT_CONFIRMED": f"Payment Confirmed - {order_id[:8]}",
            "PAYMENT_FAILED": f"Payment Failed - {order_id[:8]}",
            "FULFILLED": f"Order Shipped - {order_id[:8]}",
            "COMPLETED": f"Order Completed - {order_id[:8]}",
            "CANCELLED": f"Order Cancelled - {order_id[:8]}",
            "FAILED": f"Order Failed - {order_id[:8]}"
        }
        return subjects.get(event_type, f"Order Update - {order_id[:8]}")
