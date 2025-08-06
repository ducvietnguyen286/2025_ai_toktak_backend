from enum import Enum


class RefundStatus(Enum):
    PENDING = 0  # Ghi nhận hoàn tiền 	처리 대기 중
    PROCESSING = 1  # Đang xử lý 처리 중
    SUCCESS = 2  # Đã hoàn thành 완료됨
    CANCELLED = 2  # Hủy hoàn tiền 실패
