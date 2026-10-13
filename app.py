
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

deliveries = {}
next_id = 1

VALID_STATUSES = ["created", "in_transit", "delivered"]


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid request body"},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/deliveries", status_code=201)
async def create_delivery(request: Request):
    global next_id

    try:
        body = await request.json()
    except Exception:
        raise StarletteHTTPException(status_code=400, detail="Invalid JSON")

    if not isinstance(body, dict):
        raise StarletteHTTPException(status_code=400, detail="Body must be an object")

    recipient = body.get("recipient")
    address = body.get("address")

    if not isinstance(recipient, str) or not recipient.strip():
        raise StarletteHTTPException(status_code=400, detail="Invalid recipient")

    if not isinstance(address, str) or not address.strip():
        raise StarletteHTTPException(status_code=400, detail="Invalid address")

    delivery = {
        "id": next_id,
        "recipient": recipient,
        "address": address,
        "status": "created",
    }

    deliveries[next_id] = delivery
    next_id += 1

    return delivery


@app.get("/deliveries")
def list_deliveries(status: Optional[str] = None):
    if status is not None and status not in VALID_STATUSES:
        raise StarletteHTTPException(status_code=400, detail="Unknown status")

    result = list(deliveries.values())

    if status is not None:
        result = [d for d in result if d["status"] == status]

    return result


@app.get("/deliveries/{delivery_id}")
def get_delivery(delivery_id: int):
    delivery = deliveries.get(delivery_id)

    if delivery is None:
        raise StarletteHTTPException(status_code=404, detail="Delivery not found")

    return delivery


@app.patch("/deliveries/{delivery_id}/status")
async def update_delivery_status(delivery_id: int, request: Request):
    try:
        body = await request.json()
    except Exception:
        raise StarletteHTTPException(status_code=400, detail="Invalid JSON")

    if not isinstance(body, dict):
        raise StarletteHTTPException(status_code=400, detail="Body must be an object")

    status = body.get("status")

    if not isinstance(status, str) or status not in VALID_STATUSES:
        raise StarletteHTTPException(status_code=400, detail="Unknown status")

    delivery = deliveries.get(delivery_id)

    if delivery is None:
        raise StarletteHTTPException(status_code=404, detail="Delivery not found")

    current_index = VALID_STATUSES.index(delivery["status"])
    new_index = VALID_STATUSES.index(status)

    if new_index != current_index + 1:
        raise StarletteHTTPException(
            status_code=409,
            detail="Invalid status transition",
        )

    delivery["status"] = status
    return delivery


@app.delete("/deliveries/{delivery_id}", status_code=204)
def delete_delivery(delivery_id: int):
    delivery = deliveries.get(delivery_id)

    if delivery is None:
        raise StarletteHTTPException(status_code=404, detail="Delivery not found")

    if delivery["status"] != "created":
        raise StarletteHTTPException(
            status_code=409,
            detail="Only created deliveries can be deleted",
        )

    del deliveries[delivery_id]
    return Response(status_code=204)
