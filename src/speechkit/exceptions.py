class SpeechKitError(Exception):
    pass


class ConfigurationError(SpeechKitError):
    pass


class MediaError(SpeechKitError):
    pass


class ProviderError(SpeechKitError):
    pass
