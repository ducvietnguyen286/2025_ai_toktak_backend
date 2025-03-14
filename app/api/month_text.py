# coding: utf8
import traceback
from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from app.lib.response import Response
import pandas as pd

from app.models.month_text import MonthText
from app.services.month_text import MonthTextService

ns = Namespace(name="month-text", description="User API")


@ns.route("/random-text")
class APIRandomMonthText(Resource):

    def get(self):
        month_text = MonthTextService.random_month_text()
        return Response(
            data=month_text,
            message="Đăng nhập thành công",
        ).to_dict()


@ns.route("/import-by-excel")
class APIImportTextByExcel(Resource):

    @jwt_required()
    def post(self):
        if "file" not in request.files:
            return Response(
                message="Không tìm thấy file",
                status=400,
            ).to_dict()
        file = request.files["file"]
        if file.filename == "":
            return Response(
                message="Không tìm thấy file",
                status=400,
            ).to_dict()
        if not file.filename.endswith(".xlsx"):
            return Response(
                message="File không đúng định dạng",
                status=400,
            ).to_dict()

        try:
            df = pd.read_excel(file)
            result = []
            current_month = None
            month_data = []

            for _, row in df.iterrows():
                col1, col2 = row[0], row[1] if len(row) > 1 else ""

                if pd.isna(col1) and pd.isna(col2):
                    continue

                # Nếu gặp THANGx, lưu dữ liệu tháng cũ và bắt đầu tháng mới
                if isinstance(col1, str) and col1.startswith("THANG"):
                    if current_month:
                        result.append({"month": current_month, "data": month_data})

                    current_month = col1
                    month_data = []
                else:
                    # Thêm dữ liệu vào tháng hiện tại
                    if current_month:
                        month_data.append({"col1": col1, "col2": col2})

            # Thêm tháng cuối cùng vào result
            if current_month:
                result.append({"month": current_month, "data": month_data})

            for month in result:
                insert_value = []
                for data in month["data"]:
                    insert_value.append(
                        MonthText(
                            keyword=data["col1"],
                            hashtag=data["col2"],
                            month=month["month"],
                        )
                    )
                MonthTextService.insert_month_text(insert_value)

            return Response(
                message="Import file thành công",
                status=200,
            ).to_dict()
        except Exception as e:
            traceback.print_exc()
            print(e)
            return Response(
                message="Lỗi khi import file",
                status=400,
            ).to_dict()
