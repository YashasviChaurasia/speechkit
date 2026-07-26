class SpeechKitError(Exception):
    pass


class ConfigurationError(SpeechKitError):
    pass


class MediaError(SpeechKitError):
    pass


class UnsupportedMediaError(MediaError):
    pass


class ProviderError(SpeechKitError):
    pass


class NoSpeechError(ProviderError):
    pass
