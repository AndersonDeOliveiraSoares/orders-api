from app.exceptions.exceptions import NotFoundException, ConflictException


class ProductNotFoundException(NotFoundException):
    pass


class ProductHasOrdersException(ConflictException):
    pass
