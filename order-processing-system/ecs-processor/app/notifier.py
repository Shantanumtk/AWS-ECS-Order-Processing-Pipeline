import json
import logging
from datetime import datetime
from typing import Optional, List, Dict

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SNSNotifier:
    def __init__(self, topic_arn: str, region: str = "us-east-1"):
        self.topic_arn = topic_arn
        self.sns_client = boto3.client("sns", region_name=region)

    def send_notification(
        self,
        order_id: str,
        event_type: str,
        message: str,
        customer_name: str = None,
        customer_email: str = None,
        items: List[Dict] = None,
        total_amount: float = None,
        attributes: Optional[dict] = None
    ) -> bool:
        try:
            email_body = self._format_email_body(
                order_id=order_id,
                event_type=event_type,
                message=message,
                customer_name=customer_name,
                customer_email=customer_email,
                items=items,
                total_amount=total_amount,
                attributes=attributes
            )
            subject = self._get_subject(event_type, order_id)

            message_attributes = {
                "event_type": {"DataType": "String", "StringValue": event_type},
                "order_id": {"DataType": "String", "StringValue": order_id}
            }

            response = self.sns_client.publish(
                TopicArn=self.topic_arn,
                Message=email_body,
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

    def _format_email_body(
        self,
        order_id: str,
        event_type: str,
        message: str,
        customer_name: str = None,
        customer_email: str = None,
        items: List[Dict] = None,
        total_amount: float = None,
        attributes: Optional[dict] = None
    ) -> str:
        timestamp = datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC")
        
        status_emoji = {
            "ORDER_CREATED": "🛒",
            "PROCESSING": "⚙️",
            "PAYMENT_CONFIRMED": "💳",
            "PAYMENT_FAILED": "❌",
            "FULFILLED": "📦",
            "COMPLETED": "✅",
            "CANCELLED": "🚫",
            "FAILED": "⚠️"
        }
        
        status_title = {
            "ORDER_CREATED": "Order Received",
            "PROCESSING": "Order Processing",
            "PAYMENT_CONFIRMED": "Payment Confirmed",
            "PAYMENT_FAILED": "Payment Failed",
            "FULFILLED": "Order Shipped",
            "COMPLETED": "Order Completed",
            "CANCELLED": "Order Cancelled",
            "FAILED": "Order Issue"
        }
        
        status_message = {
            "ORDER_CREATED": "We've received your order and it's being prepared for processing.",
            "PROCESSING": "Your order is now being processed. We'll update you on the progress.",
            "PAYMENT_CONFIRMED": "Great news! Your payment has been successfully processed.",
            "PAYMENT_FAILED": "Unfortunately, we couldn't process your payment. Please check your payment details.",
            "FULFILLED": "Your order has been packed and is on its way!",
            "COMPLETED": "Your order has been completed successfully. Thank you for your purchase!",
            "CANCELLED": "Your order has been cancelled as requested.",
            "FAILED": "We encountered an issue with your order. Our team is looking into it."
        }
        
        emoji = status_emoji.get(event_type, "📋")
        title = status_title.get(event_type, "Order Update")
        friendly_message = status_message.get(event_type, message)
        
        # Header
        email_body = f"""
╔══════════════════════════════════════════════════════════════╗
                    {emoji} {title.upper()} {emoji}
╚══════════════════════════════════════════════════════════════╝

"""
        
        # Customer greeting
        if customer_name:
            email_body += f"Hello {customer_name},\n\n"
        else:
            email_body += "Hello,\n\n"
        
        email_body += f"{friendly_message}\n\n"
        
        # Order details box
        email_body += f"""
┌──────────────────────────────────────────────────────────────┐
│                      ORDER DETAILS                           │
├──────────────────────────────────────────────────────────────┤
│  Order Number:  #{order_id[:8].upper()}                              
│  Order Date:    {timestamp}
│  Status:        {title}
"""
        if customer_email:
            email_body += f"│  Email:         {customer_email}\n"
        
        email_body += "└──────────────────────────────────────────────────────────────┘\n"
        
        # Items table
        if items and len(items) > 0:
            email_body += """
┌──────────────────────────────────────────────────────────────┐
│                       ORDER ITEMS                            │
├──────────────────────────────────────────────────────────────┤
"""
            for item in items:
                product_name = item.get('product_name', 'Unknown Item')
                quantity = item.get('quantity', 1)
                unit_price = item.get('unit_price', 0)
                subtotal = item.get('subtotal', quantity * unit_price)
                
                # Truncate long product names
                if len(product_name) > 30:
                    product_name = product_name[:27] + "..."
                
                email_body += f"│  {product_name:<32}\n"
                email_body += f"│      {quantity} x ${unit_price:,.2f}                          ${subtotal:,.2f}\n"
                email_body += "│\n"
            
            email_body += "├──────────────────────────────────────────────────────────────┤\n"
            
            if total_amount is not None:
                email_body += f"│  SUBTOTAL:                                       ${total_amount:,.2f}\n"
                email_body += f"│  SHIPPING:                                       $0.00\n"
                email_body += f"│  TAX:                                            $0.00\n"
                email_body += "├──────────────────────────────────────────────────────────────┤\n"
                email_body += f"│  TOTAL:                                          ${total_amount:,.2f}\n"
            
            email_body += "└──────────────────────────────────────────────────────────────┘\n"
        
        # Status-specific additional content
        if event_type == "COMPLETED":
            email_body += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎉 Thank you for your purchase!

We hope you enjoy your order. If you have any questions or need
assistance, our customer support team is here to help.

📧 Support: support@orderprocessing.com
📞 Phone: 1-800-123-4567
🌐 Website: www.orderprocessing.com

We appreciate your business and look forward to serving you again!

"""
        elif event_type == "PAYMENT_FAILED":
            email_body += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  WHAT TO DO NEXT:

   1. Verify your payment details are correct
   2. Ensure sufficient funds are available
   3. Try placing your order again

If you continue to experience issues, please contact our support team.

📧 Support: support@orderprocessing.com
📞 Phone: 1-800-123-4567

"""
        elif event_type == "FULFILLED":
            email_body += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 SHIPPING INFORMATION

Your order is on its way! Estimated delivery: 3-5 business days

Track your package using your Order Number above.

"""
        elif event_type == "PAYMENT_CONFIRMED":
            email_body += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💳 Your payment has been processed successfully.

Your order will be prepared for shipping shortly. You'll receive
another notification when your order ships.

"""
        
        # Footer
        email_body += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is an automated message from Order Processing System.
Please do not reply directly to this email.

© 2025 Order Processing Inc. All rights reserved.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        return email_body

    def _get_subject(self, event_type: str, order_id: str) -> str:
        short_id = order_id[:8].upper()
        subjects = {
            "ORDER_CREATED": f"🛒 Order Confirmed - #{short_id}",
            "PROCESSING": f"⚙️ Processing Your Order - #{short_id}",
            "PAYMENT_CONFIRMED": f"💳 Payment Received - #{short_id}",
            "PAYMENT_FAILED": f"❌ Payment Issue - #{short_id}",
            "FULFILLED": f"📦 Your Order Has Shipped! - #{short_id}",
            "COMPLETED": f"✅ Order Delivered - #{short_id}",
            "CANCELLED": f"🚫 Order Cancelled - #{short_id}",
            "FAILED": f"⚠️ Order Issue - #{short_id}"
        }
        return subjects.get(event_type, f"📋 Order Update - #{short_id}")