class AppException(Exception):
    """Exceção base da aplicação."""

    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class NotFoundException(AppException):
    """Recurso não encontrado."""

    status_code = 404


class ConflictException(AppException):
    """Conflito com o estado atual do recurso."""

    status_code = 409