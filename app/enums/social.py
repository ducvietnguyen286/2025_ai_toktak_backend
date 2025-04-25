class SocialMedia:
    """
    Enum for social media platforms.
    """

    PUBLISHED = "PUBLISHED"
    ERRORED = "ERRORED"

    FACEBOOK = "FACEBOOK"
    TWITTER = "X-TWITTER"
    THREAD = "THREAD"
    INSTAGRAM = "INSTAGRAM"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"

    @classmethod
    def choices(cls):
        return [
            (attr, attr)
            for attr in dir(cls)
            if not attr.startswith("__") and not callable(getattr(cls, attr))
        ]
