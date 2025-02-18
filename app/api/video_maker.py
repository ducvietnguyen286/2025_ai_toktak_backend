# coding: utf8
import json
from flask_restx import Namespace, Resource
from flask import request
from app.services.video_service import create_video_from_images

ns = Namespace(name="video_maker", description="Video Maker API")


@ns.route("/video_status/<string:video_id>")
class VideoStatus(Resource):
    def get(self, video_id):
        # Giả lập trả về JSON cho video_id
        return {
            "status": "success",
            "video_id": video_id,
            "message": "Video status retrieved successfully XXXX TTTT XXX CCCC  TTT",
        }


@ns.route("/create_video")
class CreateVideo(Resource):
    def post(self):
        # Lấy dữ liệu từ request
        data = request.get_json()
        images_url = data["images_url"]  # Đây là một list các URL của hình ảnh
        
        if 'product_name' not in data or 'images_url' not in data:
            return {'message': 'Missing required fields (product_name or images_url)'}, 400

        product_name = data['product_name']
        
        

        if not isinstance(images_url, list):
            return {"message": "images_url must be a list of URLs"}, 400

        for url in images_url:
            if not isinstance(url, str):
                return {"message": "Each URL must be a string"}, 400
            
        
        result = create_video_from_images(product_name, images_url)
        print(result)
        
        render_id = ""
        status = True
        message = f"Video  created successfully"
        if result['status_code'] == 200:
            render_id = result['response']
        else:
            status = False
            message = result['message']
            
        
        return {
            "status": status,
            "message": message,
            "render_id": render_id,
        }
