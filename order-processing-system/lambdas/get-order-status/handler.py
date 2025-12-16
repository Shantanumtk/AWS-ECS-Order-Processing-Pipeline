import os
from typing import List, Optional

import psycopg2
from fastapi import FastAPI, HTTPException, Path, Query
from mangum import Mangum
from pydantic import BaseModel

app = FastAPI(title="Get Order Status Service", version="1.0.0")

DB_HOST = os.environ.get("DB_HOST")
DB_NAME = os.environ.get("DB_NAME")
DB_USERNAME = os.environ.get("DB_USERNAME")
DB_PASSWORD = os.environ.get("DB_PASSWORD")


class OrderItemResponse(BaseModel):
    id: str
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float


class StatusLogEntry(BaseModel):
    status: str
    message: Optional[str]
    created_at: str


class OrderResponse(BaseModel):
    order_id: str
    customer_email: str
    customer_name: str
    total_amount: float
    status: str
    items: List[OrderItemResponse]
    status_history: List[StatusLogEntry]
    created_at: str
    updated_at: str


class OrderListItem(BaseModel):
    order_id: str
    customer_email: str
    customer_name: str
    total_amount: float
    status: str
    created_at: str


class OrderListResponse(BaseModel):
    orders: List[OrderListItem]
    total_count: int


def get_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USERNAME, password=DB_PASSWORD)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "get-order-status"}


@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str = Path(..., description="Order ID (UUID)")):
    try:
        conn = get_db_connection()

        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, customer_email, customer_name, total_amount, status, created_at, updated_at FROM orders WHERE id = %s",
                (order_id,)
            )
            order_row = cur.fetchone()

            if not order_row:
                raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

            order = {
                "order_id": str(order_row[0]),
                "customer_email": order_row[1],
                "customer_name": order_row[2],
                "total_amount": float(order_row[3]),
                "status": order_row[4],
                "created_at": order_row[5].isoformat() if order_row[5] else None,
                "updated_at": order_row[6].isoformat() if order_row[6] else None
            }

            cur.execute("SELECT id, product_name, quantity, unit_price, subtotal FROM order_items WHERE order_id = %s", (order_id,))
            items = [OrderItemResponse(id=str(r[0]), product_name=r[1], quantity=r[2], unit_price=float(r[3]), subtotal=float(r[4])) for r in cur.fetchall()]

            cur.execute("SELECT status, message, created_at FROM order_status_log WHERE order_id = %s ORDER BY created_at DESC", (order_id,))
            status_history = [StatusLogEntry(status=r[0], message=r[1], created_at=r[2].isoformat() if r[2] else None) for r in cur.fetchall()]

        conn.close()

        return OrderResponse(
            order_id=order["order_id"],
            customer_email=order["customer_email"],
            customer_name=order["customer_name"],
            total_amount=order["total_amount"],
            status=order["status"],
            items=items,
            status_history=status_history,
            created_at=order["created_at"],
            updated_at=order["updated_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve order: {str(e)}")


@app.get("/orders", response_model=OrderListResponse)
async def list_orders(
    status: Optional[str] = Query(None),
    customer_email: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    try:
        conn = get_db_connection()

        with conn.cursor() as cur:
            query = "SELECT id, customer_email, customer_name, total_amount, status, created_at FROM orders WHERE 1=1"
            count_query = "SELECT COUNT(*) FROM orders WHERE 1=1"
            params = []

            if status:
                query += " AND status = %s"
                count_query += " AND status = %s"
                params.append(status)

            if customer_email:
                query += " AND customer_email = %s"
                count_query += " AND customer_email = %s"
                params.append(customer_email)

            cur.execute(count_query, params)
            total_count = cur.fetchone()[0]

            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cur.execute(query, params)
            orders = [
                OrderListItem(
                    order_id=str(r[0]),
                    customer_email=r[1],
                    customer_name=r[2],
                    total_amount=float(r[3]),
                    status=r[4],
                    created_at=r[5].isoformat() if r[5] else None
                ) for r in cur.fetchall()
            ]

        conn.close()

        return OrderListResponse(orders=orders, total_count=total_count)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list orders: {str(e)}")


handler = Mangum(app, lifespan="off", api_gateway_base_path="/dev")