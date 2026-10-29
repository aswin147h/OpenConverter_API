class ConversionError(Exception):
    """Safe-to-show error. Message must never contain paths or file contents."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
