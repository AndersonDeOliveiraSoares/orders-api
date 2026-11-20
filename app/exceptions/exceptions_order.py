from app.exceptions.exceptions import (
    ConflictException,
    NotFoundException,
)


class CustomerNotFoundException(NotFoundException):
    """Cliente não encontrado."""


class ProductNotFoundException(NotFoundException):
    """Produto não encontrado."""


class OrderNotFoundException(NotFoundException):
    """Pedido não encontrado."""


class InsufficientStockException(ConflictException):
    """Estoque insuficiente para atender ao pedido."""


class InvalidOrderStatusException(ConflictException):
    """Transição de status não permitida."""
