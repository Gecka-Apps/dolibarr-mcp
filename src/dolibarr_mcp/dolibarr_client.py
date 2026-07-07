"""Professional Dolibarr API client with comprehensive CRUD operations."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from .config import Config


class DolibarrAPIError(Exception):
    """Custom exception for Dolibarr API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class DolibarrValidationError(DolibarrAPIError):
    """Raised for client-side validation failures before hitting the API."""


class DolibarrClient:
    """Professional Dolibarr API client with comprehensive functionality."""
    
    def __init__(self, config: Config):
        """Initialize the Dolibarr client."""
        self.config = config
        self.base_url = config.dolibarr_url.rstrip('/')
        self.api_key = config.api_key
        self.session: Optional[ClientSession] = None
        self.logger = logging.getLogger(__name__)
        self.debug_mode = getattr(config, "debug_mode", False)
        self.allow_ref_autogen = getattr(config, "allow_ref_autogen", False)
        self.ref_autogen_prefix = getattr(config, "ref_autogen_prefix", "AUTO")
        self.max_retries = getattr(config, "max_retries", 2)
        self.retry_backoff_seconds = getattr(config, "retry_backoff_seconds", 0.5)
        
        # Configure timeout
        self.timeout = ClientTimeout(total=30, connect=10)
        self.logger.setLevel(config.log_level)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_session()
    
    async def start_session(self):
        """Start the HTTP session."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers={
                    "DOLAPIKEY": self.api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
    
    async def close_session(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

    @staticmethod
    def _extract_identifier(response: Any) -> Any:
        """Return the identifier from Dolibarr responses when available."""
        if isinstance(response, dict):
            if "id" in response:
                return response["id"]
            success = response.get("success")
            if isinstance(success, dict) and "id" in success:
                return success["id"]
        return response

    @staticmethod
    def _merge_payload(data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Merge an optional dictionary with keyword overrides."""
        payload: Dict[str, Any] = {}
        if data:
            payload.update(data)
        if kwargs:
            payload.update(kwargs)
        return payload

    
    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Public helper retained for compatibility with legacy integrations and tests."""
        return await self._make_request(method, endpoint, params=params, data=data)

    def _build_url(self, endpoint: str) -> str:
        """Build full API URL."""
        endpoint = endpoint.lstrip('/')
        base = self.base_url.rstrip('/')

        if endpoint == "status":
            base_without_index = base.replace('/index.php', '')
            return f"{base_without_index}/status"

        return f"{base}/{endpoint}"

    def _mask_api_key(self) -> str:
        """Return a masked representation of the API key for logging."""
        if not self.api_key:
            return "<not-set>"
        if len(self.api_key) <= 6:
            return "*" * len(self.api_key)
        return f"{self.api_key[:2]}***{self.api_key[-2:]}"

    @staticmethod
    def _now_iso() -> str:
        """Return current UTC timestamp in ISO format with Z suffix."""
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    @staticmethod
    def _generate_correlation_id() -> str:
        """Create a unique correlation identifier."""
        return str(uuid4())

    def _generate_reference(self) -> str:
        """Generate a unique reference using prefix, timestamp, and a UUID suffix."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        suffix = uuid4().hex[:8]
        return f"{self.ref_autogen_prefix}_{timestamp}_{suffix}"

    def _build_validation_error(
        self,
        endpoint: str,
        missing_fields: Optional[List[str]] = None,
        invalid_fields: Optional[List[Dict[str, str]]] = None,
        message: str = "Validation failed",
        status: int = 400,
    ) -> Dict[str, Any]:
        """Build a structured validation error response."""
        return {
            "error": "Bad Request",
            "status": status,
            "message": message,
            "missing_fields": missing_fields or [],
            "invalid_fields": invalid_fields or [],
            "endpoint": f"/{endpoint.lstrip('/')}",
            "timestamp": self._now_iso(),
        }

    def _build_internal_error(self, endpoint: str, message: str, correlation_id: str) -> Dict[str, Any]:
        """Build a structured internal server error response."""
        return {
            "error": "Internal Server Error",
            "status": 500,
            "message": message,
            "correlation_id": correlation_id,
            "endpoint": f"/{endpoint.lstrip('/')}",
            "timestamp": self._now_iso(),
        }

    def _apply_aliases(self, payload: Dict[str, Any], aliases: Dict[str, List[str]]) -> None:
        """Promote alias fields to canonical names."""
        for target, options in aliases.items():
            if target not in payload:
                for alias in options:
                    if alias in payload and payload[alias] not in (None, ""):
                        payload[target] = payload.pop(alias)
                        break

    def _validate_payload(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        required_fields: List[str],
        aliases: Optional[Dict[str, List[str]]] = None,
        numeric_positive: Optional[List[str]] = None,
        enum_fields: Optional[Dict[str, List[Any]]] = None,
        required_any_of: Optional[List[List[str]]] = None,
        non_empty_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Validate payload before sending to Dolibarr and optionally auto-generate refs."""
        aliases = aliases or {}
        numeric_positive = numeric_positive or []
        enum_fields = enum_fields or {}
        required_any_of = required_any_of or []
        non_empty_fields = non_empty_fields or []

        self._apply_aliases(payload, aliases)

        missing_fields = [
            field
            for field in required_fields
            if field not in payload or payload[field] in (None, "")
        ]

        invalid_fields: List[Dict[str, str]] = []

        for group in required_any_of:
            if all(payload.get(field) in (None, "") for field in group):
                missing_fields.append(" or ".join(group))

        for field in non_empty_fields:
            if field in payload and payload[field] in (None, "") and field not in missing_fields:
                missing_fields.append(field)

        for field in numeric_positive:
            if field in payload and isinstance(payload[field], (int, float)) and payload[field] < 0:
                invalid_fields.append({"field": field, "message": "must be a positive number"})

        for field, values in enum_fields.items():
            if field in payload and payload[field] not in values:
                invalid_fields.append({"field": field, "message": f"must be one of {values}"})

        if "ref" in missing_fields and self.allow_ref_autogen:
            payload["ref"] = self._generate_reference()
            missing_fields = [f for f in missing_fields if f != "ref"]

        if missing_fields or invalid_fields:
            details: List[str] = []
            if missing_fields:
                details.append(f"missing: {', '.join(missing_fields)}")
            if invalid_fields:
                details.append(
                    "invalid: "
                    + ", ".join(f["field"] for f in invalid_fields)
                )
            message = "Validation failed" + (f" ({'; '.join(details)})" if details else "")
            error_data = self._build_validation_error(
                endpoint=endpoint,
                missing_fields=missing_fields,
                invalid_fields=invalid_fields,
                message=message,
            )
            raise DolibarrValidationError(
                message=error_data["message"],
                status_code=error_data["status"],
                response_data=error_data,
            )

        return payload

    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Dolibarr API."""
        if not self.session:
            await self.start_session()
        
        url = self._build_url(endpoint)
        
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                if self.debug_mode:
                    self.logger.debug(
                        "Making %s request to %s with params=%s payload_keys=%s api_key=%s",
                        method,
                        url,
                        params or {},
                        list((data or {}).keys()),
                        self._mask_api_key(),
                    )
                
                kwargs = {
                    "params": params or {},
                }
                
                if data and method.upper() in ["POST", "PUT"]:
                    kwargs["json"] = data
                
                async with self.session.request(method, url, **kwargs) as response:
                    response_text = await response.text()
                    
                    # Log response for debugging without leaking secrets
                    if self.debug_mode:
                        self.logger.debug("Response status: %s", response.status)
                        self.logger.debug("Response body (truncated): %s", response_text[:500])
                    
                    # Try to parse JSON response
                    try:
                        response_data = json.loads(response_text) if response_text else {}
                    except json.JSONDecodeError:
                        response_data = {"raw_response": response_text}
                    
                    # Handle error responses
                    if response.status >= 400:
                        if response.status == 400:
                            missing = []
                            invalid: List[Dict[str, str]] = []
                            if isinstance(response_data, dict):
                                if "missing_fields" in response_data:
                                    missing = response_data.get("missing_fields") or []
                                if "invalid_fields" in response_data:
                                    invalid = response_data.get("invalid_fields") or []
                                # Heuristic: derive missing ref from message
                                if not missing and isinstance(response_data.get("error"), str):
                                    if "ref" in response_data.get("error").lower():
                                        missing.append("ref")
                                if not missing and "message" in response_data and "ref" in str(response_data["message"]).lower():
                                    missing.append("ref")
                            error_data = self._build_validation_error(
                                endpoint=endpoint,
                                missing_fields=missing,
                                invalid_fields=invalid,
                                message="Validation failed",
                            )
                            raise DolibarrValidationError(
                                message=error_data["message"],
                                status_code=400,
                                response_data=error_data,
                            )

                        if response.status >= 500:
                            correlation_id = self._generate_correlation_id()
                            internal_error = self._build_internal_error(
                                endpoint=endpoint,
                                message=response_data.get("message", f"An unexpected error occurred while processing {endpoint}"),
                                correlation_id=correlation_id,
                            )
                            self.logger.error(
                                "Server error %s for %s (correlation_id=%s): %s",
                                response.status,
                                endpoint,
                                correlation_id,
                                response_text[:500],
                            )
                            raise DolibarrAPIError(
                                message=internal_error["message"],
                                status_code=response.status,
                                response_data=internal_error,
                            )

                        error_msg = f"HTTP {response.status}: {response.reason}"
                        if isinstance(response_data, dict):
                            if "message" in response_data:
                                error_msg = response_data["message"]
                            elif "error" in response_data and isinstance(response_data["error"], str):
                                error_msg = response_data["error"]
                        raise DolibarrAPIError(
                            message=error_msg,
                            status_code=response.status,
                            response_data=response_data,
                        )
                    
                    return response_data
                    
            except aiohttp.ClientError as e:
                last_exception = e
                if endpoint == "status" and not url.endswith("/api/status"):
                    try:
                        alt_url = f"{self.base_url}/setup/modules"
                        self.logger.debug(f"Status failed, trying alternative: {alt_url}")
                        
                        async with self.session.get(alt_url) as response:
                            if response.status == 200:
                                return {
                                    "success": 1,
                                    "dolibarr_version": "API Available",
                                    "api_version": "1.0"
                                }
                    except Exception as alt_exc:  # pylint: disable=broad-except
                        last_exception = alt_exc

                if attempt < self.max_retries and isinstance(e, aiohttp.ClientResponseError) and e.status in {502, 503, 504}:
                    backoff = self.retry_backoff_seconds * (2 ** attempt)
                    await asyncio.sleep(backoff)
                    continue
                break
            except DolibarrAPIError:
                raise
            except Exception as e:  # pylint: disable=broad-except
                last_exception = e
                break

        if isinstance(last_exception, DolibarrAPIError):
            raise last_exception

        if isinstance(last_exception, Exception):
            correlation_id = self._generate_correlation_id()
            internal_error = self._build_internal_error(
                endpoint=endpoint,
                message=str(last_exception),
                correlation_id=correlation_id,
            )
            self.logger.error(
                "Unexpected error during %s %s (correlation_id=%s): %s",
                method,
                endpoint,
                correlation_id,
                last_exception,
            )
            raise DolibarrAPIError(
                message=internal_error["message"],
                status_code=500,
                response_data=internal_error,
            ) from last_exception

        raise DolibarrAPIError(f"HTTP client error: {endpoint}")
    
    # ============================================================================
    # SYSTEM ENDPOINTS
    # ============================================================================
    
    async def test_connection(self) -> Dict[str, Any]:
        """Compatibility helper that proxies to get_status."""
        return await self.get_status()

    async def get_status(self) -> Dict[str, Any]:
        """Get API status and version information."""
        try:
            # First try the standard status endpoint
            return await self.request("GET", "status")
        except DolibarrAPIError:
            # If status fails, try to get module list as a connectivity test
            try:
                result = await self.request("GET", "setup/modules")
                if result:
                    return {
                        "success": 1,
                        "dolibarr_version": "Connected",
                        "api_version": "1.0",
                        "modules_available": isinstance(result, (list, dict))
                    }
            except:
                pass
            
            # If all else fails, try a simple user list
            try:
                result = await self.request("GET", "users?limit=1")
                if result is not None:
                    return {
                        "success": 1,
                        "dolibarr_version": "API Working",
                        "api_version": "1.0"
                    }
            except:
                raise DolibarrAPIError("Cannot connect to Dolibarr API. Please check your configuration.")

    async def get_company_country_id(self) -> Optional[int]:
        """Return the configured company's country id (used to scope tax rates)."""
        try:
            company = await self.request("GET", "setup/company")
        except DolibarrAPIError:
            return None
        country = company.get("country_id") if isinstance(company, dict) else None
        return int(country) if country not in (None, "", 0, "0") else None

    async def get_vat_rates(
        self,
        country_id: Optional[int] = None,
        active: int = 1,
    ) -> List[Dict[str, Any]]:
        """List tax rates (VAT / TGC) from Dolibarr's tax dictionary.

        Defaults to the company's country so the caller gets the rates that apply
        to its invoices/orders (e.g. TGC rates in New Caledonia).
        """
        if country_id is None:
            country_id = await self.get_company_country_id()
        params: Dict[str, Any] = {"active": active, "limit": 100}
        if country_id is not None:
            params["fk_country"] = country_id
        result = await self.request("GET", "setup/dictionary/vat", params=params)
        rows = result if isinstance(result, list) else []
        rates = []
        for r in rows:
            rate = {
                "rate": float(r.get("taux", 0)),
                "code": r.get("code") or None,
                "note": r.get("note"),
            }
            # Surface local taxes only when they are actually set.
            for lt in ("localtax1", "localtax2"):
                if r.get(lt) not in (None, "", "0", 0):
                    rate[lt] = r[lt]
            rates.append(rate)
        return rates

    # ============================================================================
    # USER MANAGEMENT
    # ============================================================================
    
    @staticmethod
    def _add_list_params(
        params: Dict[str, Any],
        *,
        page: int = 1,
        sortfield: Optional[str] = None,
        sortorder: Optional[str] = None,
        properties: Optional[str] = None,
    ) -> None:
        """Inject common pagination/sort/properties params into *params*."""
        if page > 1:
            params["page"] = page
        if sortfield:
            params["sortfield"] = sortfield
            params["sortorder"] = sortorder or "ASC"
        if properties:
            params["properties"] = properties

    async def get_users(
        self,
        limit: int = 100,
        page: int = 1,
        sortfield: Optional[str] = None,
        sortorder: Optional[str] = None,
        properties: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of users."""
        params: Dict[str, Any] = {"limit": limit}
        self._add_list_params(params, page=page, sortfield=sortfield, sortorder=sortorder, properties=properties)
        result = await self.request("GET", "users", params=params)
        return result if isinstance(result, list) else []
    
    async def get_user_by_id(self, user_id: int) -> Dict[str, Any]:
        """Get specific user by ID."""
        return await self.request("GET", f"users/{user_id}")
    
    async def create_user(
        self,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a new user."""
        payload = self._merge_payload(data, **kwargs)
        result = await self.request("POST", "users", data=payload)
        return self._extract_identifier(result)

    async def update_user(
        self,
        user_id: int,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Update an existing user."""
        payload = self._merge_payload(data, **kwargs)
        return await self.request("PUT", f"users/{user_id}", data=payload)

    async def delete_user(self, user_id: int) -> Dict[str, Any]:
        """Delete a user."""
        return await self.request("DELETE", f"users/{user_id}")
    
    # ============================================================================
    # CUSTOMER/THIRD PARTY MANAGEMENT
    # ============================================================================
    
    async def search_customers(
        self,
        sqlfilters: str,
        limit: int = 20,
        properties: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search customers using SQL filters."""
        params: Dict[str, Any] = {"limit": limit, "sqlfilters": sqlfilters}
        if properties:
            params["properties"] = properties
        result = await self.request("GET", "thirdparties", params=params)
        return result if isinstance(result, list) else []

    async def get_customers(
        self,
        limit: int = 100,
        page: int = 1,
        sortfield: Optional[str] = None,
        sortorder: Optional[str] = None,
        properties: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of customers/third parties."""
        params: Dict[str, Any] = {"limit": limit}
        self._add_list_params(params, page=page, sortfield=sortfield, sortorder=sortorder, properties=properties)
        result = await self.request("GET", "thirdparties", params=params)
        return result if isinstance(result, list) else []
    
    async def get_customer_by_id(self, customer_id: int) -> Dict[str, Any]:
        """Get specific customer by ID."""
        return await self.request("GET", f"thirdparties/{customer_id}")
    
    async def create_customer(
        self,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a new customer/third party."""
        payload = self._merge_payload(data, **kwargs)

        type_value = payload.pop("type", None)
        if type_value is not None:
            payload.setdefault("client", 1 if type_value in (1, 3) else 0)
            payload.setdefault("fournisseur", 1 if type_value in (2, 3) else 0)
        else:
            payload.setdefault("client", 1)

        # "-1" tells Dolibarr to auto-generate the accounting code via its
        # numbering module (required at API level with mask-based numbering).
        if payload.get("client"):
            payload.setdefault("code_client", "-1")
        if payload.get("fournisseur"):
            payload.setdefault("code_fournisseur", "-1")

        payload.setdefault("status", payload.get("status", 1))
        payload.setdefault("country_id", payload.get("country_id", 1))

        result = await self.request("POST", "thirdparties", data=payload)
        return self._extract_identifier(result)

    async def update_customer(
        self,
        customer_id: int,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Update an existing customer."""
        payload = self._merge_payload(data, **kwargs)

        type_value = payload.pop("type", None)
        if type_value is not None:
            payload["client"] = 1 if type_value in (1, 3) else 0
            payload["fournisseur"] = 1 if type_value in (2, 3) else 0

        return await self.request("PUT", f"thirdparties/{customer_id}", data=payload)

    async def delete_customer(self, customer_id: int) -> Dict[str, Any]:
        """Delete a customer."""
        return await self.request("DELETE", f"thirdparties/{customer_id}")
    
    # ============================================================================
    # PRODUCT MANAGEMENT
    # ============================================================================
    
    async def search_products(
        self,
        sqlfilters: str,
        limit: int = 20,
        properties: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search products using SQL filters."""
        params: Dict[str, Any] = {"limit": limit, "sqlfilters": sqlfilters}
        if properties:
            params["properties"] = properties
        result = await self.request("GET", "products", params=params)
        return result if isinstance(result, list) else []

    async def get_products(
        self,
        limit: int = 100,
        page: int = 1,
        sortfield: Optional[str] = None,
        sortorder: Optional[str] = None,
        properties: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of products."""
        params: Dict[str, Any] = {"limit": limit}
        self._add_list_params(params, page=page, sortfield=sortfield, sortorder=sortorder, properties=properties)
        result = await self.request("GET", "products", params=params)
        return result if isinstance(result, list) else []
    
    async def get_product_by_id(self, product_id: int) -> Dict[str, Any]:
        """Get specific product by ID."""
        return await self.request("GET", f"products/{product_id}")
    
    async def create_product(
        self,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a new product or service."""
        payload = self._merge_payload(data, **kwargs)
        payload = self._validate_payload(
            endpoint="products",
            payload=payload,
            required_fields=["ref", "label", "type"],
            aliases={"label": ["name"]},
            numeric_positive=["price", "price_ttc"],
            enum_fields={"type": ["product", "service", 0, 1]},
            required_any_of=[["price", "price_ttc"]],
            non_empty_fields=["price", "price_ttc", "tva_tx"],
        )
        result = await self.request("POST", "products", data=payload)
        return self._extract_identifier(result)

    async def update_product(
        self,
        product_id: int,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Update an existing product."""
        payload = self._merge_payload(data, **kwargs)
        return await self.request("PUT", f"products/{product_id}", data=payload)

    async def delete_product(self, product_id: int) -> Dict[str, Any]:
        """Delete a product."""
        return await self.request("DELETE", f"products/{product_id}")

    async def get_product_purchase_prices(self, product_id: int) -> List[Dict[str, Any]]:
        """List supplier (purchase) prices for a product."""
        result = await self.request("GET", f"products/{product_id}/purchase_prices")
        return result if isinstance(result, list) else []

    async def add_product_purchase_price(
        self,
        product_id: int,
        supplier_id: int,
        price: float,
        supplier_ref: str,
        qty: float = 1,
        tva_tx: float = 0,
        price_base_type: str = "HT",
        availability: int = 0,
    ) -> Dict[str, Any]:
        """Add a supplier price tier for a product (ref_fourn is required by Dolibarr).

        When the multicurrency module is enabled, Dolibarr's update_buyprice
        overwrites buyprice with multicurrency_buyprice / multicurrency_tx, so we
        also pass multicurrency_buyprice=price (tx defaults to 1). Harmless when
        multicurrency is off (that branch is skipped and buyprice is used directly).
        """
        payload = {
            "qty": qty,
            "buyprice": price,
            "price_base_type": price_base_type,
            "fourn_id": supplier_id,
            "availability": availability,
            "ref_fourn": supplier_ref,
            "tva_tx": tva_tx,
            "multicurrency_buyprice": price,
            "multicurrency_price_base_type": price_base_type,
        }
        return await self.request("POST", f"products/{product_id}/purchase_prices", data=payload)

    async def delete_product_purchase_price(self, product_id: int, price_id: int) -> Dict[str, Any]:
        """Delete one supplier price tier from a product."""
        return await self.request("DELETE", f"products/{product_id}/purchase_prices/{price_id}")

    # ============================================================================
    # INVOICE MANAGEMENT
    # ============================================================================
    
    async def get_invoices(
        self,
        limit: int = 100,
        page: int = 1,
        status: Optional[str] = None,
        sortfield: Optional[str] = None,
        sortorder: Optional[str] = None,
        properties: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of invoices."""
        params: Dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        self._add_list_params(params, page=page, sortfield=sortfield, sortorder=sortorder, properties=properties)
        result = await self.request("GET", "invoices", params=params)
        return result if isinstance(result, list) else []
    
    async def get_invoice_by_id(self, invoice_id: int) -> Dict[str, Any]:
        """Get specific invoice by ID including invoice lines.
        
        Note: Dolibarr API separates invoice header and lines into different endpoints.
        This method combines both to provide complete invoice data including lines.
        """
        invoice = await self.request("GET", f"invoices/{invoice_id}")
        
        # Fetch invoice lines separately (Dolibarr API design)
        try:
            lines = await self.request("GET", f"invoices/{invoice_id}/lines")
            invoice['lines'] = lines if isinstance(lines, list) else []
        except DolibarrAPIError as e:
            # If lines endpoint fails, return invoice without lines
            # This ensures backward compatibility with older Dolibarr versions
            self.logger.warning(
                "Failed to fetch lines for invoice %s: %s",
                invoice_id,
                str(e)
            )
            invoice['lines'] = []
        
        return invoice
    
    async def create_invoice(
        self,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a new invoice."""
        payload = self._merge_payload(data, **kwargs)

        # Fix: Map customer_id to socid
        if "customer_id" in payload and "socid" not in payload:
            payload["socid"] = payload.pop("customer_id")

        # Fix: Map product_id to fk_product in lines
        if "lines" in payload and isinstance(payload["lines"], list):
            for line in payload["lines"]:
                if "product_id" in line:
                    line["fk_product"] = line.pop("product_id")
                # Ensure product_type is passed if present (0=Product, 1=Service)
                if "product_type" in line:
                    line["product_type"] = line["product_type"]

        payload = self._validate_payload(
            endpoint="invoices",
            payload=payload,
            required_fields=["socid"],
        )

        result = await self.request("POST", "invoices", data=payload)
        return self._extract_identifier(result)

    async def update_invoice(
        self,
        invoice_id: int,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Update an existing invoice."""
        payload = self._merge_payload(data, **kwargs)
        return await self.request("PUT", f"invoices/{invoice_id}", data=payload)

    async def delete_invoice(self, invoice_id: int) -> Dict[str, Any]:
        """Delete an invoice."""
        return await self.request("DELETE", f"invoices/{invoice_id}")

    async def add_invoice_line(
        self,
        invoice_id: int,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Add a line to an invoice."""
        payload = self._merge_payload(data, **kwargs)
        
        # Map product_id to fk_product if present
        if "product_id" in payload:
            payload["fk_product"] = payload.pop("product_id")
            
        return await self.request("POST", f"invoices/{invoice_id}/lines", data=payload)

    async def update_invoice_line(
        self,
        invoice_id: int,
        line_id: int,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Update a line in an invoice, preserving fields that are not provided.

        Dolibarr's line PUT is a full replace, so a partial payload would blank
        the omitted fields. We fetch the current line and overlay only the
        provided values.
        """
        updates = self._merge_payload(data, **kwargs)
        payload = updates
        invoice = await self.get_invoice_by_id(invoice_id)
        lines = invoice.get("lines", []) if isinstance(invoice, dict) else []
        current = next(
            (l for l in lines if str(l.get("id") or l.get("rowid")) == str(line_id)),
            None,
        )
        if current is not None:
            preserved = ("desc", "subprice", "qty", "tva_tx", "product_type", "fk_product", "remise_percent")
            base = {k: current[k] for k in preserved if current.get(k) is not None}
            base.update(updates)
            payload = base
        return await self.request("PUT", f"invoices/{invoice_id}/lines/{line_id}", data=payload)

    async def delete_invoice_line(self, invoice_id: int, line_id: int) -> Dict[str, Any]:
        """Delete a line from an invoice."""
        return await self.request("DELETE", f"invoices/{invoice_id}/lines/{line_id}")

    async def validate_invoice(self, invoice_id: int, warehouse_id: int = 0, not_trigger: int = 0) -> Dict[str, Any]:
        """Validate an invoice."""
        payload = {
            "idwarehouse": warehouse_id,
            "not_trigger": not_trigger
        }
        return await self.request("POST", f"invoices/{invoice_id}/validate", data=payload)

    async def search_invoices(
        self,
        customer_id: Optional[int] = None,
        status: Optional[int] = None,
        limit: int = 20,
        properties: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search invoices by customer and/or status (fk_statut: 0 draft, 1 unpaid, 2 paid, 3 abandoned)."""
        filters = []
        if customer_id is not None:
            filters.append(f"(t.fk_soc:=:{customer_id})")
        if status is not None:
            filters.append(f"(t.fk_statut:=:{status})")
        params: Dict[str, Any] = {"limit": limit, "sortfield": "t.rowid", "sortorder": "DESC"}
        if filters:
            params["sqlfilters"] = " and ".join(filters)
        if properties:
            params["properties"] = properties
        result = await self.request("GET", "invoices", params=params)
        return result if isinstance(result, list) else []

    async def set_invoice_to_draft(self, invoice_id: int, idwarehouse: int = -1) -> Dict[str, Any]:
        """Revert a validated invoice back to draft (idwarehouse=-1 = no stock movement)."""
        return await self.request("POST", f"invoices/{invoice_id}/settodraft", data={"idwarehouse": idwarehouse})

    async def get_bank_accounts(self) -> List[Dict[str, Any]]:
        """List the Dolibarr bank accounts."""
        result = await self.request("GET", "bankaccounts", params={"limit": 100})
        return result if isinstance(result, list) else []

    async def get_payment_modes(self) -> List[Dict[str, Any]]:
        """List the payment types from Dolibarr's dictionary."""
        result = await self.request("GET", "setup/dictionary/payment_types", params={"limit": 100})
        return result if isinstance(result, list) else []

    async def add_payment_to_invoice(
        self,
        invoice_id: int,
        date: str,
        payment_mode_id: Optional[int] = None,
        account_id: Optional[int] = None,
        num_payment: str = "",
        close_paid: bool = True,
    ) -> Dict[str, Any]:
        """Register a payment for the full remaining amount of an invoice.

        Resolves the bank account and payment mode automatically when not given:
        the single configured bank account, and the wire-transfer ("VIR") payment
        mode (or the first available). Raises with a clear message when the choice
        is ambiguous.
        """
        if account_id is None:
            accounts = await self.get_bank_accounts()
            if not accounts:
                raise DolibarrAPIError("No bank accounts configured in Dolibarr; set account_id.")
            if len(accounts) > 1:
                listing = ", ".join(f"{a.get('id')}: {a.get('label') or a.get('ref')}" for a in accounts)
                raise DolibarrAPIError(f"Multiple bank accounts; specify account_id. Available: {listing}")
            account_id = accounts[0].get("id")
        if payment_mode_id is None:
            modes = await self.get_payment_modes()
            if not modes:
                raise DolibarrAPIError("No payment modes configured in Dolibarr; set payment_mode_id.")
            chosen = next((m for m in modes if m.get("code") == "VIR"), modes[0])
            payment_mode_id = chosen.get("id") or chosen.get("rowid")
        payload = {
            "datepaye": date,
            "paymentid": payment_mode_id,
            "closepaidinvoices": "yes" if close_paid else "no",
            "accountid": account_id,
            "num_payment": num_payment or "",
        }
        return await self.request("POST", f"invoices/{invoice_id}/payments", data=payload)

    # ============================================================================
    # ORDER MANAGEMENT
    # ============================================================================
    
    async def get_orders(
        self,
        limit: int = 100,
        page: int = 1,
        status: Optional[str] = None,
        sortfield: Optional[str] = None,
        sortorder: Optional[str] = None,
        properties: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of orders."""
        params: Dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        self._add_list_params(params, page=page, sortfield=sortfield, sortorder=sortorder, properties=properties)
        result = await self.request("GET", "orders", params=params)
        return result if isinstance(result, list) else []
    
    async def get_order_by_id(self, order_id: int) -> Dict[str, Any]:
        """Get specific order by ID."""
        return await self.request("GET", f"orders/{order_id}")
    
    async def create_order(
        self,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a new order."""
        payload = self._merge_payload(data, **kwargs)
        result = await self.request("POST", "orders", data=payload)
        return self._extract_identifier(result)

    async def update_order(
        self,
        order_id: int,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Update an existing order."""
        payload = self._merge_payload(data, **kwargs)
        return await self.request("PUT", f"orders/{order_id}", data=payload)

    async def delete_order(self, order_id: int) -> Dict[str, Any]:
        """Delete an order."""
        return await self.request("DELETE", f"orders/{order_id}")

    async def add_order_line(
        self,
        order_id: int,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Add a line to a customer order."""
        payload = self._merge_payload(data, **kwargs)
        if "product_id" in payload:
            payload["fk_product"] = payload.pop("product_id")
        return await self.request("POST", f"orders/{order_id}/lines", data=payload)

    async def update_order_line(
        self,
        order_id: int,
        line_id: int,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Update an order line, preserving fields that are not provided.

        Like invoice lines, Dolibarr's order line PUT is a full replace, so we
        fetch the current line and overlay only the provided values.
        """
        updates = self._merge_payload(data, **kwargs)
        if "product_id" in updates:
            updates["fk_product"] = updates.pop("product_id")
        payload = updates
        order = await self.get_order_by_id(order_id)
        lines = order.get("lines", []) if isinstance(order, dict) else []
        current = next(
            (l for l in lines if str(l.get("id") or l.get("rowid")) == str(line_id)),
            None,
        )
        if current is not None:
            preserved = ("desc", "subprice", "qty", "tva_tx", "product_type", "fk_product", "remise_percent")
            base = {k: current[k] for k in preserved if current.get(k) is not None}
            base.update(updates)
            payload = base
        return await self.request("PUT", f"orders/{order_id}/lines/{line_id}", data=payload)

    async def delete_order_line(self, order_id: int, line_id: int) -> Dict[str, Any]:
        """Delete a line from a customer order."""
        return await self.request("DELETE", f"orders/{order_id}/lines/{line_id}")

    # ============================================================================
    # PROPOSAL (QUOTE / DEVIS) MANAGEMENT
    # ============================================================================

    async def get_proposals(
        self,
        limit: int = 100,
        page: int = 1,
        status: Optional[int] = None,
        sortfield: Optional[str] = None,
        sortorder: Optional[str] = None,
        properties: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of proposals (fk_statut: 0 draft, 1 open, 2 signed, 3 declined, 4 billed)."""
        params: Dict[str, Any] = {"limit": limit}
        if status is not None:
            params["sqlfilters"] = f"(t.fk_statut:=:{status})"
        self._add_list_params(params, page=page, sortfield=sortfield, sortorder=sortorder, properties=properties)
        result = await self.request("GET", "proposals", params=params)
        return result if isinstance(result, list) else []

    async def get_proposal_by_id(self, proposal_id: int) -> Dict[str, Any]:
        """Get a specific proposal by ID, including its lines."""
        return await self.request("GET", f"proposals/{proposal_id}")

    async def create_proposal(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Create a new proposal (draft)."""
        payload = self._merge_payload(data, **kwargs)
        if "customer_id" in payload and "socid" not in payload:
            payload["socid"] = payload.pop("customer_id")
        if "project_id" in payload and "fk_projet" not in payload:
            payload["fk_projet"] = payload.pop("project_id")
        if isinstance(payload.get("lines"), list):
            for line in payload["lines"]:
                if isinstance(line, dict) and "product_id" in line and "fk_product" not in line:
                    line["fk_product"] = line.pop("product_id")
        payload = self._validate_payload(endpoint="proposals", payload=payload, required_fields=["socid"])
        result = await self.request("POST", "proposals", data=payload)
        return self._extract_identifier(result)

    async def update_proposal(self, proposal_id: int, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Update an existing proposal (draft only)."""
        payload = self._merge_payload(data, **kwargs)
        if "project_id" in payload and "fk_projet" not in payload:
            payload["fk_projet"] = payload.pop("project_id")
        return await self.request("PUT", f"proposals/{proposal_id}", data=payload)

    async def delete_proposal(self, proposal_id: int) -> Dict[str, Any]:
        """Delete a proposal."""
        return await self.request("DELETE", f"proposals/{proposal_id}")

    async def add_proposal_line(self, proposal_id: int, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Add a line to a proposal.

        Uses the singular POST {id}/line route: the plural /lines route expects an
        array of lines and silently creates a blank line when given a single dict.
        """
        payload = self._merge_payload(data, **kwargs)
        if "product_id" in payload:
            payload["fk_product"] = payload.pop("product_id")
        return await self.request("POST", f"proposals/{proposal_id}/line", data=payload)

    async def update_proposal_line(
        self,
        proposal_id: int,
        line_id: int,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Update a proposal line, preserving fields that are not provided."""
        updates = self._merge_payload(data, **kwargs)
        if "product_id" in updates:
            updates["fk_product"] = updates.pop("product_id")
        payload = updates
        proposal = await self.get_proposal_by_id(proposal_id)
        lines = proposal.get("lines", []) if isinstance(proposal, dict) else []
        current = next(
            (l for l in lines if str(l.get("id") or l.get("rowid")) == str(line_id)),
            None,
        )
        if current is not None:
            preserved = ("desc", "subprice", "qty", "tva_tx", "product_type", "fk_product", "remise_percent")
            base = {k: current[k] for k in preserved if current.get(k) is not None}
            base.update(updates)
            payload = base
        return await self.request("PUT", f"proposals/{proposal_id}/lines/{line_id}", data=payload)

    async def delete_proposal_line(self, proposal_id: int, line_id: int) -> Dict[str, Any]:
        """Delete a line from a proposal."""
        return await self.request("DELETE", f"proposals/{proposal_id}/lines/{line_id}")

    async def validate_proposal(self, proposal_id: int) -> Dict[str, Any]:
        """Validate a proposal (draft -> open), assigning its ref."""
        return await self.request("POST", f"proposals/{proposal_id}/validate", data={})

    async def sign_proposal(self, proposal_id: int, note: Optional[str] = None) -> Dict[str, Any]:
        """Sign a proposal (open -> signed / accepted).

        The close route takes the target status in the body (status 2 = signed).
        """
        payload: Dict[str, Any] = {"status": 2}
        if note:
            payload["note_private"] = note
        return await self.request("POST", f"proposals/{proposal_id}/close", data=payload)

    async def convert_proposal_to_order(self, proposal_id: int) -> Dict[str, Any]:
        """Convert a signed proposal into a customer order; returns the new order id.

        Conversion lives on the orders API (POST /orders/createfromproposal/{id}).
        """
        result = await self.request("POST", f"orders/createfromproposal/{proposal_id}", data={})
        return self._extract_identifier(result)

    # ============================================================================
    # CONTACT MANAGEMENT
    # ============================================================================
    
    async def get_contacts(
        self,
        limit: int = 100,
        page: int = 1,
        sortfield: Optional[str] = None,
        sortorder: Optional[str] = None,
        properties: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of contacts."""
        params: Dict[str, Any] = {"limit": limit}
        self._add_list_params(params, page=page, sortfield=sortfield, sortorder=sortorder, properties=properties)
        result = await self.request("GET", "contacts", params=params)
        return result if isinstance(result, list) else []
    
    async def get_contact_by_id(self, contact_id: int) -> Dict[str, Any]:
        """Get specific contact by ID."""
        return await self.request("GET", f"contacts/{contact_id}")
    
    async def create_contact(
        self,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a new contact."""
        payload = self._merge_payload(data, **kwargs)
        result = await self.request("POST", "contacts", data=payload)
        return self._extract_identifier(result)

    async def update_contact(
        self,
        contact_id: int,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Update an existing contact."""
        payload = self._merge_payload(data, **kwargs)
        return await self.request("PUT", f"contacts/{contact_id}", data=payload)

    async def delete_contact(self, contact_id: int) -> Dict[str, Any]:
        """Delete a contact."""
        return await self.request("DELETE", f"contacts/{contact_id}")
    
    # ============================================================================
    # PROJECT MANAGEMENT
    # ============================================================================
    
    async def get_projects(
        self,
        limit: int = 100,
        page: int = 1,
        status: Optional[int] = None,
        sortfield: Optional[str] = None,
        sortorder: Optional[str] = None,
        properties: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of projects."""
        params: Dict[str, Any] = {"limit": limit}
        if status is not None:
            # Dolibarr ignores a `status` query param on /projects; filter via USF.
            params["sqlfilters"] = f"(t.fk_statut:=:{status})"
        self._add_list_params(params, page=page, sortfield=sortfield, sortorder=sortorder, properties=properties)
        result = await self.request("GET", "projects", params=params)
        return result if isinstance(result, list) else []

    async def get_project_by_id(self, project_id: int) -> Dict[str, Any]:
        """Get specific project by ID."""
        return await self.request("GET", f"projects/{project_id}")

    async def search_projects(
        self,
        sqlfilters: str,
        limit: int = 20,
        properties: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search projects using SQL filters."""
        params: Dict[str, Any] = {"limit": limit, "sqlfilters": sqlfilters}
        if properties:
            params["properties"] = properties
        result = await self.request("GET", "projects", params=params)
        return result if isinstance(result, list) else []

    async def create_project(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Create a new project."""
        payload = self._merge_payload(data, **kwargs)
        # Let Dolibarr's numbering module assign the ref; a customer is optional.
        payload.setdefault("ref", "auto")
        # Dolibarr's /projects endpoint expects `title`, not `name`.
        payload = self._validate_payload(
            endpoint="projects",
            payload=payload,
            required_fields=["title"],
            aliases={"title": ["name"]},
        )
        result = await self.request("POST", "projects", data=payload)
        return self._extract_identifier(result)

    async def update_project(self, project_id: int, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Update an existing project."""
        payload = self._merge_payload(data, **kwargs)
        return await self.request("PUT", f"projects/{project_id}", data=payload)

    async def delete_project(self, project_id: int) -> Dict[str, Any]:
        """Delete a project."""
        return await self.request("DELETE", f"projects/{project_id}")

    # ============================================================================
    # CATEGORY MANAGEMENT
    # ============================================================================

    async def get_categories(
        self,
        type: str = "product",
        limit: int = 100,
        page: int = 1,
        sortfield: Optional[str] = None,
        sortorder: Optional[str] = None,
        properties: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of categories filtered by type."""
        type_map = {"product": "0", "customer": "1", "supplier": "2",
                     "contact": "3", "member": "4"}
        params: Dict[str, Any] = {
            "limit": limit,
            "type": type_map.get(type, type),
        }
        self._add_list_params(params, page=page, sortfield=sortfield,
                              sortorder=sortorder, properties=properties)
        result = await self.request("GET", "categories", params=params)
        return result if isinstance(result, list) else []

    async def search_categories(
        self,
        sqlfilters: str,
        type: str = "product",
        limit: int = 20,
        properties: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search categories using SQL filters."""
        type_map = {"product": "0", "customer": "1", "supplier": "2",
                     "contact": "3", "member": "4"}
        params: Dict[str, Any] = {
            "limit": limit,
            "type": type_map.get(type, type),
            "sqlfilters": sqlfilters,
        }
        if properties:
            params["properties"] = properties
        result = await self.request("GET", "categories", params=params)
        return result if isinstance(result, list) else []

    async def get_products_by_category(
        self,
        category_id: int,
        limit: int = 100,
        properties: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get products belonging to a category."""
        params: Dict[str, Any] = {"limit": limit, "type": "product"}
        if properties:
            params["properties"] = properties
        result = await self.request(
            "GET", f"categories/{category_id}/objects", params=params,
        )
        return result if isinstance(result, list) else []

    async def get_product_categories(
        self,
        product_id: int,
    ) -> List[Dict[str, Any]]:
        """Get categories assigned to a product."""
        result = await self.request("GET", f"products/{product_id}/categories")
        return result if isinstance(result, list) else []

    # ============================================================================
    # RAW API CALL
    # ============================================================================
    
    async def dolibarr_raw_api(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make raw API call to any Dolibarr endpoint."""
        return await self.request(method, endpoint, params=params, data=data)
