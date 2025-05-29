# coding: utf8
import json
from flask_restx import Namespace, Resource
from app.decorators import parameters, required_admin
from app.lib.response import Response
from app.extensions import redis_client
from app.services.link import LinkService
from app.services.user import UserService
from app.services.youtube_client import YoutubeClientService

ns = Namespace(name="youtube_client", description="Youtube API")


@ns.route("/list")
class APIListYoutubeClient(Resource):

    @required_admin
    def get(self):
        youtube_clients = YoutubeClientService.get_youtube_clients()
        return Response(
            data=[youtube_client._to_json() for youtube_client in youtube_clients],
            message="Lấy danh sách thành công",
        ).to_dict()


@ns.route("/<int:id>")
class APIFindYoutubeClient(Resource):

    @required_admin
    def get(self, id):
        youtube_client = YoutubeClientService.find_client_by_id(id)
        if not youtube_client:
            return Response(
                message="Không tìm thấy youtube_client",
                status=400,
            ).to_dict()

        return Response(
            data=youtube_client._to_json(),
            message="Lây youtube_client thành công",
        ).to_dict()


@ns.route("/create")
class APICreateYoutubeClient(Resource):

    @required_admin
    @parameters(
        type="object",
        properties={
            "project_name": {"type": "string"},
            "client_id": {"type": "string"},
            "client_secret": {"type": "string"},
        },
        required=["project_name", "client_id", "client_secret"],
    )
    def post(self, args):
        project_name = args.get("project_name", "")
        client_id = args.get("client_id", "")
        client_secret = args.get("client_secret", {})
        youtube_client = YoutubeClientService.create_youtube_client(
            project_name=project_name,
            client_id=client_id,
            client_secret=client_secret,
        )

        all_clients = YoutubeClientService.get_youtube_clients()
        all_clients = [client._to_json() for client in all_clients]
        redis_client.set("toktak:all_clients", json.dumps(all_clients))

        return Response(
            data=youtube_client._to_json(),
            message="Tạo youtube_client thành công",
        ).to_dict()


@ns.route("/update")
class APIUpdateYoutubeClient(Resource):

    @required_admin
    @parameters(
        type="object",
        properties={
            "id": {"type": ["string", "number", "null"]},
            "project_name": {"type": "string"},
            "client_id": {"type": "string"},
            "client_secret": {"type": "string"},
        },
        required=[],
    )
    def put(self, args):
        id = args.pop("id", None)
        id = int(id) if id else 0
        if not id:
            return Response(
                message="ID không hợp lệ",
                status=400,
            ).to_dict()

        youtube_client = YoutubeClientService.update_youtube_client(id, **args)

        all_clients = YoutubeClientService.get_youtube_clients()
        all_clients = [client._to_json() for client in all_clients]
        redis_client.set("toktak:all_clients", json.dumps(all_clients))

        return Response(
            data=youtube_client._to_json(),
            message="Tạo youtube_client thành công",
        ).to_dict()


@ns.route("/update-all-users-to-client")
class APIUpdateUsersToClient(Resource):

    @required_admin
    @parameters(
        type="object",
        properties={
            "id": {"type": ["string", "number", "null"]},
        },
        required=[],
    )
    def put(self, args):
        id = args.pop("id", None)
        id = int(id) if id else 0
        if not id:
            return Response(
                message="ID không hợp lệ",
                status=400,
            ).to_dict()

        youtube_client = YoutubeClientService.find_client_by_id(id)
        if not youtube_client:
            return Response(
                message="Không tìm thấy youtube_client",
                status=400,
            ).to_dict()

        users = UserService.all_users()
        user_ids = [user.get("id") for user in users]
        youtube_client.user_ids = json.dumps(user_ids)
        youtube_client.member_count = len(user_ids)
        youtube_client.save()

        links = LinkService.get_links()
        youtube_link = None
        for link in links:
            if link.get("type") == "YOUTUBE":
                youtube_link = link
                break

        if youtube_link:
            UserService.update_by_link_multiple_user_links(
                youtube_link.get("id"),
                youtube_client=json.dumps(youtube_client._to_json()),
            )

        return Response(
            data=youtube_client._to_json(),
            message="Tạo youtube_client thành công",
        ).to_dict()
