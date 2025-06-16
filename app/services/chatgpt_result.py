from app.models.chatgpt_results import ChatGPTResult
from app.lib.query import (
    delete_by_id,
    select_with_filter,
    select_by_id,
    select_with_filter_one,
)


class ChatGPTResultService:

    @staticmethod
    def create_chatgpt_result(*args, **kwargs):
        chatgpt_result = ChatGPTResult(*args, **kwargs)
        chatgpt_result.save()
        return chatgpt_result

    @staticmethod
    def find_chatgpt_result(id):
        chatgpt_result = select_by_id(ChatGPTResult, id)
        return chatgpt_result

    @staticmethod
    def find_one_chatgpt_result_by_filter(**kwargs):
        filters = []
        for key, value in kwargs.items():
            if hasattr(ChatGPTResult, key):
                filters.append(getattr(ChatGPTResult, key) == value)
        chatgpt_result = select_with_filter_one(
            ChatGPTResult, filters=filters, order_by=[ChatGPTResult.id.desc()]
        )
        return chatgpt_result

    @staticmethod
    def get_chatgpt_results():
        chatgpt_results = select_with_filter(
            ChatGPTResult,
            order_by=[ChatGPTResult.id.desc()],
            filters=[ChatGPTResult.status == 1],
        )
        return [chatgpt_result._to_json() for chatgpt_result in chatgpt_results]

    @staticmethod
    def update_chatgpt_result(id, *args, **kwargs):
        chatgpt_result = ChatGPTResult.query.get(id)
        chatgpt_result.update(**kwargs)
        return chatgpt_result

    @staticmethod
    def delete_chatgpt_result(id):
        delete_by_id(ChatGPTResult, id)
        return True
