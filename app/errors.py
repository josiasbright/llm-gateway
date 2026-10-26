"""Erreurs renvoyees au client dans le meme format que l'API d'OpenAI."""


class GatewayError(Exception):
    def __init__(
        self,
        status_code: int,
        message: str,
        code: str,
        error_type: str = "invalid_request_error",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.code = code
        self.error_type = error_type

    def body(self) -> dict[str, dict[str, str]]:
        return {"error": {"message": self.message, "type": self.error_type, "code": self.code}}
