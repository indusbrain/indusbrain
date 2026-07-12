from fastapi import Request
from fastapi.responses import JSONResponse
import logging

# Configure local terminal logging matrices to capture diagnostic telemetry
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IndustryOS_Safety_Layer")

class IndustrialBaseException(Exception):
    """
    Foundational Architectural Exception class from which all domain-specific 
    industrial errors safely derive.
    """
    def __init__(self, message: str, error_code: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code

class AssetNotFoundException(IndustrialBaseException):
    """
    Thrown explicitly when an engineer attempts to fetch a machine, manual, 
    or database index record that does not exist in our system.
    """
    def __init__(self, message: str = "Requested industrial asset could not be located."):
        super().__init__(message=message, error_code="ERR_ASSET_NOT_FOUND", status_code=404)

class ComplianceViolationException(IndustrialBaseException):
    """
    Thrown explicitly when an AI agent or manual calculation execution loop 
    detects an operational parameter that violates safety constraints.
    """
    def __init__(self, message: str = "Critical operation halted due to safety regulatory breach."):
        super().__init__(message=message, error_code="ERR_COMPLIANCE_BREACH", status_code=403)


# Keep ONLY the custom domain handler here
async def industrial_exception_handler(request: Request, exc: IndustrialBaseException) -> JSONResponse:
    """
    Catches domain exceptions and formats them into standard corporate JSON models.
    """
    logger.warning(f"🚨 INTERCEPTED DOMAIN ERROR [{exc.error_code}]: {exc.message} at route {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
            "system_telemetry": "Active"
        }
    )