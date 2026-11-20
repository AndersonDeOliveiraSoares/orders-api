from app.exceptions.exceptions import ConflictException, NotFoundException


class CustomerNotFoundException(NotFoundException):
    """Cliente não encontrado."""


class CustomerEmailAlreadyExistsException(ConflictException):
    """E-mail já cadastrado para outro cliente."""


class CustomerHasOrdersException(ConflictException):
    """Não é permitido excluir cliente que possui pedidos."""
