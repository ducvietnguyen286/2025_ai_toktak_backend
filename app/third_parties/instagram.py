from app.third_parties.base_service import BaseService


class InstagramService(BaseService):
    def __init__(self, sync_id=""):
        self.sync_id = sync_id
        self.user_link = None
        self.user = None
        self.link = None
        self.meta = None
        self.social_post = None
        self.user_id = None
        self.link_id = None
        self.post_id = None
        self.batch_id = None
        self.service = "INSTAGRAM"

    def send_post(self, post, link, user_id, social_post_id):
        pass
