class GatewayError(Exception):
    def __init__(
        self,
        status_code: int,
        message: str,
        code: str,
        error_type: str = "invalid_request_error",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.code = code
        self.error_type = error_type
        self.headers = headers

    def body(self) -> dict[str, dict[str, str]]:
        return {"error": {"message": self.message, "type": self.error_type, "code": self.code}}
