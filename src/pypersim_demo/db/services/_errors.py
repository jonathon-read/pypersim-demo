class DatabaseServicesError(Exception):
    def __init__(self, message: str, code: str = "DB_ERROR"):
        super().__init__(message)
        self.code = code
