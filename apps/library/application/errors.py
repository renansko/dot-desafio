class ApplicationError(Exception):
    """Base for errors that can cross an application boundary."""


class InvalidBook(ApplicationError):
    def __init__(self, errors: dict[str, list[str]]) -> None:
        super().__init__("Livro inválido.")
        self.errors = errors


class DependencyUnavailable(ApplicationError):
    pass


class ExternalTimeout(ApplicationError):
    pass
