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
        posts = Post.query.where(Post.status == 1).all()
        return [post._to_json() for post in posts]

    @staticmethod
    def update_post(id, *args, **kwargs):
        post = Post.query.get(id)
        post.update(**kwargs)
        return post

    @staticmethod
    def delete_post(id):
        return Post.query.get(id).delete()

    @staticmethod
    def get_posts_by_batch_id(batch_id):
        posts = Post.query.where(Post.batch_id == batch_id).all()
        return [post._to_json() for post in posts]
