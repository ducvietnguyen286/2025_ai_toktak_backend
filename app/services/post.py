from app.models.post import Post


class PostService:

    @staticmethod
    def create_post(*args, **kwargs):
        post = Post(*args, **kwargs)
        post.save()
        return post

    @staticmethod
    def find_post(id):
        return Post.query.get(id)

    @staticmethod
    def get_posts():
        return Post.query.where(Post.status == 1).all()

    @staticmethod
    def update_post(id, *args, **kwargs):
        post = Post.query.get(id)
        post.update(*args, **kwargs)
        return post

    @staticmethod
    def delete_post(id):
        return Post.query.get(id).delete()
