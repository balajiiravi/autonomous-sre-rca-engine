
import uuid
import httpx
import uvicorn

from fastapi import FastAPI, HTTPException, Request

from simulator.logging_config import (
    configure_logging,
    get_service_logger,
    request_id_context
)

# Initialize logging
configure_logging()

app = FastAPI(
    title="Autonomous SRE RCA - Failure Simulator",
    version="0.1.0"
)

SERVICE_BASE_URL = "http://127.0.0.1:8000"

# Independent service loggers
frontend_logger = get_service_logger("frontend-service")
payment_logger = get_service_logger("payment-service")
db_logger = get_service_logger("inventory-db")

# Deterministic chaos switch
db_pool_exhausted = False


# --------------------------------------------------
# REQUEST CORRELATION MIDDLEWARE
# --------------------------------------------------

@app.middleware("http")
async def correlation_middleware(
    request: Request,
    call_next
):
    request_id = request.headers.get(
        "X-Request-ID",
        str(uuid.uuid4())
    )

    token = request_id_context.set(request_id)

    try:
        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        return response

    finally:
        request_id_context.reset(token)


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health():
    return {"status": "healthy"}


# --------------------------------------------------
# CHAOS INJECTION
# --------------------------------------------------

@app.get("/simulate-chaos")
def inject_chaos():

    global db_pool_exhausted

    db_pool_exhausted = True

    db_logger.warning(
        "CHAOS INJECTION: Database connection pool exhaustion activated."
    )

    return {
        "status": "success",
        "failure": "inventory-db connection pool exhausted"
    }


# --------------------------------------------------
# SYSTEM RESET
# --------------------------------------------------

@app.get("/reset-system")
def reset_system():

    global db_pool_exhausted

    db_pool_exhausted = False

    db_logger.info(
        "CHAOS RESET: Database restored to healthy state."
    )

    return {
        "status": "success",
        "message": "System restored."
    }


# --------------------------------------------------
# FRONTEND SERVICE
# --------------------------------------------------

@app.get("/checkout")
async def checkout():

    frontend_logger.info(
        "Checkout request received from browser."
    )

    try:

        async with httpx.AsyncClient(
            timeout=2.0
        ) as client:

            response = await client.get(
                f"{SERVICE_BASE_URL}/process-payment",
                headers={
                    "X-Request-ID": request_id_context.get()
                }
            )

            response.raise_for_status()

            frontend_logger.info(
                "Checkout completed successfully."
            )

            return {
                "status": "Order Success",
                "payload": response.json()
            }

    except httpx.TimeoutException:

        frontend_logger.error(
            "HTTP 504: Payment service request timed out."
        )

        raise HTTPException(
            status_code=504,
            detail="Gateway timeout during checkout."
        )

    except httpx.HTTPStatusError as exc:

        frontend_logger.error(
            "HTTP 504: Payment dependency returned status %s.",
            exc.response.status_code
        )

        raise HTTPException(
            status_code=504,
            detail="Upstream payment processing failure."
        )


# --------------------------------------------------
# PAYMENT SERVICE
# --------------------------------------------------

@app.get("/process-payment")
async def process_payment():

    payment_logger.info(
        "Payment initiated. Validating inventory availability."
    )

    try:

        async with httpx.AsyncClient(
            timeout=1.5
        ) as client:

            response = await client.get(
                f"{SERVICE_BASE_URL}/query-inventory",
                headers={
                    "X-Request-ID": request_id_context.get()
                }
            )

            response.raise_for_status()

            payment_logger.info(
                "Inventory validation successful. Payment settled."
            )

            return {
                "payment_status": "settled",
                "inventory": response.json()
            }

    except httpx.TimeoutException:

        payment_logger.error(
            "Database validation timed out after 1500ms."
        )

        raise HTTPException(
            status_code=500,
            detail="Payment processing timeout."
        )

    except httpx.HTTPStatusError as exc:

        payment_logger.error(
            "Inventory dependency failed with HTTP %s.",
            exc.response.status_code
        )

        raise HTTPException(
            status_code=500,
            detail="Payment transaction could not complete."
        )


# --------------------------------------------------
# INVENTORY DATABASE SERVICE
# --------------------------------------------------

@app.get("/query-inventory")
def query_inventory():

    global db_pool_exhausted

    if db_pool_exhausted:

        db_logger.critical(
            "CONNECTION POOL EXHAUSTED: "
            "50/50 sessions occupied. "
            "New requests blocked waiting for connections."
        )

        raise HTTPException(
            status_code=500,
            detail="Database connection pool exhausted."
        )

    db_logger.info(
        "Connection pool healthy: 4/50 sessions occupied."
    )

    return {
        "available_stock": 142,
        "status": "SYNCED"
    }


# --------------------------------------------------
# APPLICATION ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_config=None
    )
