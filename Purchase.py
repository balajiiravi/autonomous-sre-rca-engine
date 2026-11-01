import uvicorn
from fastapi import FastAPI, HTTPException
import httpx
import logging
from datetime import datetime

# Define a completely explicit File Handler to completely bypass Uvicorn's internal loops
file_handler = logging.FileHandler("production_telemetry.log", mode="a")
log_formatter = logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(log_formatter)

# Set up explicit loggers for our three distinct microservices
def get_service_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    # Prevent logs from bubbling up and duplicating in Uvicorn's server stream
    logger.propagate = False 
    logger.addHandler(file_handler)
    return logger

frontend_logger = get_service_logger("frontend-service")
payment_logger = get_service_logger("payment-service")
db_logger = get_service_logger("inventory-db")

Payment = FastAPI(title="SRE RAG Mock Microservice Architecture Pool")
db_pool_exhausted = False

@Payment.get("/simulate-chaos")
def inject_chaos():
    global db_pool_exhausted
    db_pool_exhausted = True
    return {"status": "success", "message": "Chaos injected: inventory-db connection pool has been exhausted."}

@Payment.get("/reset-system")
def reset_system():
    global db_pool_exhausted
    db_pool_exhausted = False
    return {"status": "success", "message": "System restored to healthy operational benchmarks."}

@Payment.get("/checkout")
async def frontend_checkout_route():
    frontend_logger.info("HTTP GET /checkout initiated by user browser session context.")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://127.0.0", timeout=2.0)
            if response.status_code != 200:
                raise HTTPException(status_code=504, detail="Upstream transaction processing fault.")
            
            frontend_logger.info("HTTP 200 Order processed successfully. Checkout complete.")
            return {"status": "Order Success", "payload": response.json()}
            
        except httpx.TimeoutException:
            frontend_logger.error("HTTP POST /checkout failed - Status 504 Gateway Timeout from backend service.")
            raise HTTPException(status_code=504, detail="Gateway Timeout across internal microservice routing meshes.")

@Payment.get("/process-payment")
async def payment_processing_route():
    payment_logger.info("Token authorized for transaction payload. Validating ledger records...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://127.0.0", timeout=1.5)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Database write allocation barrier hit.")
            
            return {"payment_status": "settled", "inventory_reservation": response.json()}
            
        except (httpx.TimeoutException, httpx.HTTPStatusError):
            payment_logger.error("Upstream timeout on database commit validation loop. Execution halted after 1500ms.")
            raise HTTPException(status_code=500, detail="Internal transactional processing breakdown.")

@Payment.get("/query-inventory")
def inventory_database_route():
    global db_pool_exhausted
    if db_pool_exhausted:
        db_logger.critical("Connection pool exhausted! Max 50 active sessions reached. Threads blocked waiting for resource allocations.")
        raise HTTPException(status_code=500, detail="Internal Server Error: Driver operational pool deadlock context.")
        
    db_logger.info("Connection pool active: 4/50 allocations used. Ledger read/write queries successfully committed.")
    return {"available_stock": 142, "status": "SYNCED"}

if __name__ == "__main__":
    # Start server locally
    uvicorn.run(Payment, host="127.0.0.1", port=8000)
