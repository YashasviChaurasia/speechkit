class SpeechKitError(Exception):
    pass


class ConfigurationError(SpeechKitError):
    pass


class MediaError(SpeechKitError):
    pass


class UnsupportedMediaError(MediaError):
    pass


class ProviderError(SpeechKitError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class NoSpeechError(ProviderError):
    pass
