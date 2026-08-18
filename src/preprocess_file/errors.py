class PreprocessError(Exception):
    """Base error for the preprocessing pipeline."""


class FileTooLargeError(PreprocessError):
    pass


class EncryptedFileError(PreprocessError):
    pass


class UnsupportedTypeError(PreprocessError):
    pass


class UnsafeArchiveError(PreprocessError):
    pass


class RecursionLimitError(PreprocessError):
    pass
