import json
import os
import uuid
from datetime import datetime
from typing import List

import boto3
import logging
import psycopg2
from fastapi import FastAPI, HTTPException
from mangum import Mangum
from pydantic import BaseModel, EmailStr, Field



logger = logging.getLogger()
logger.setLevel(logging.INFO)

app = FastAPI(title="Create Order Service", version="1.0.0")

DB_HOST = os.environ.get("DB_HOST")
DB_NAME = os.environ.get("DB_NAME")
DB_USERNAME = os.environ.get("DB_USERNAME")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

sqs_client = boto3.client("sqs", region_name=AWS_REGION)


class OrderItem(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)


class CreateOrderRequest(BaseModel):
    customer_email: EmailStr
    customer_name: str = Field(..., min_length=1, max_length=255)
    items: List[OrderItem] = Field(..., min_length=1)


class OrderItemResponse(BaseModel):
    id: str
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float


class CreateOrderResponse(BaseModel):
    order_id: str
    customer_email: str
    customer_name: str
    total_amount: float
    status: str
    items: List[OrderItemResponse]
    created_at: str
    message: str


def get_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USERNAME, password=DB_PASSWORD)


def create_tables_if_not_exist(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id UUID PRIMARY KEY,
                customer_email VARCHAR(255) NOT NULL,
                customer_name VARCHAR(255) NOT NULL,
                total_amount DECIMAL(10, 2) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS order_items (
                id UUID PRIMARY KEY,
                order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
                product_name VARCHAR(255) NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price DECIMAL(10, 2) NOT NULL,
                subtotal DECIMAL(10, 2) NOT NULL
            );
            CREATE TABLE IF NOT EXISTS order_status_log (
                id UUID PRIMARY KEY,
                order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
                status VARCHAR(50) NOT NULL,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
            CREATE INDEX IF NOT EXISTS idx_orders_customer_email ON orders(customer_email);
            CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
            CREATE INDEX IF NOT EXISTS idx_order_status_log_order_id ON order_status_log(order_id);
        """)
        conn.commit()


def send_to_sqs(order_id: str, order_data: dict):
    message_body = {
        "order_id": order_id,
        "customer_email": order_data["customer_email"],
        "customer_name": order_data["customer_name"],
        "total_amount": order_data["total_amount"],
        "items": order_data["items"],
        "created_at": order_data["created_at"]
    }
    sqs_client.send_message(
        QueueUrl=SQS_QUEUE_URL,
        MessageBody=json.dumps(message_body),
        MessageAttributes={"OrderId": {"DataType": "String", "StringValue": order_id}}
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "create-order"}


@app.post("/orders", response_model=CreateOrderResponse)
async def create_order(request: CreateOrderRequest):
    order_id = str(uuid.uuid4())
    created_at = datetime.utcnow()

    items_with_subtotal = []
    total_amount = 0.0

    for item in request.items:
        subtotal = round(item.quantity * item.unit_price, 2)
        total_amount += subtotal
        items_with_subtotal.append({
            "id": str(uuid.uuid4()),
            "product_name": item.product_name,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "subtotal": subtotal
        })

    total_amount = round(total_amount, 2)

    try:
        conn = get_db_connection()
        create_tables_if_not_exist(conn)

        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO orders (id, customer_email, customer_name, total_amount, status, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (order_id, request.customer_email, request.customer_name, total_amount, "PENDING", created_at, created_at)
            )

            for item in items_with_subtotal:
                cur.execute(
                    "INSERT INTO order_items (id, order_id, product_name, quantity, unit_price, subtotal) VALUES (%s, %s, %s, %s, %s, %s)",
                    (item["id"], order_id, item["product_name"], item["quantity"], item["unit_price"], item["subtotal"])
                )

            cur.execute(
                "INSERT INTO order_status_log (id, order_id, status, message) VALUES (%s, %s, %s, %s)",
                (str(uuid.uuid4()), order_id, "PENDING", "Order created and queued for processing")
            )
            conn.commit()

        conn.close()

        order_data = {
            "customer_email": request.customer_email,
            "customer_name": request.customer_name,
            "total_amount": total_amount,
            "items": items_with_subtotal,
            "created_at": created_at.isoformat()
        }
        send_to_sqs(order_id, order_data)

        return CreateOrderResponse(
            order_id=order_id,
            customer_email=request.customer_email,
            customer_name=request.customer_name,
            total_amount=total_amount,
            status="PENDING",
            items=[OrderItemResponse(**item) for item in items_with_subtotal],
            created_at=created_at.isoformat(),
            message="Order created successfully and queued for processing"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")


handler = Mangum(app, lifespan="off")

def handler(event, context):
    import json
    logger.info(f"EVENT: {json.dumps(event)}")
    logger.info(f"HTTP Method: {event.get('requestContext', {}).get('http', {}).get('method')}")
    logger.info(f"Path: {event.get('rawPath')}")
    return mangum_handler(event, context)