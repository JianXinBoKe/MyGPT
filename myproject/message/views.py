from django.shortcuts import render

# Create your views here.
from rest_framework import serializers
from rest_framework.views import APIView

from message.models import UsersMessages
from rest_framework.response import Response

from openaigpt.aigpt import get_chat_response
from datetime import datetime

class UsersMessagesSerializers(serializers.ModelSerializer):
    # date = serializers.DateField(source="pub_date")
    class Meta:
        model = UsersMessages
        # fields = "__all__"
        # fields = ["title","price"]
        exclude = ["valid"]


class UsersMessagesView(APIView):

    def get(self,request):    #获取某个用户的历史聊天记录
        #获取所有书籍
        print(request.GET.get('userid'))
        message_list = UsersMessages.objects.filter(userid = request.GET.get('userid'),valid=1)
        # message_list = UsersMessages.objects.filter(userid = request.data['userid'],valid=1)

        #构建序列化器对象
        #instance序列化
        #data反序列化
        #many序列化一个模型类对象还是多个
        serializer = UsersMessagesSerializers(instance=message_list,many=True)

        return Response(serializer.data)

    def post(self,request):    #处理某个用户请求中的问题
        #获取请求数据
        requestData = request.data
        # print("data:",requestData)

        record_count = UsersMessages.objects.filter(userid=request.data['userid'],valid=1).count()
        record_count = record_count if record_count < 5 else 5   #要从数据库读取的信息数量
        old_messages = UsersMessages.objects.filter(userid = request.data['userid'],valid=1).order_by('-id')[:record_count] #获取前5条消息
        #构建请求问题上下文
        messages = [{"role": "system", "content": "你是中国产出的人工智能机器人"}]
        for obj in old_messages:
            messages.append({"role": "user", "content": obj.question_text})
            messages.append({"role": "assistant", "content": obj.result_text})
        messages.append({"role": "user", "content": request.data['question_text']})

        #调用接口，发送给chatgpt
        result_text = get_chat_response(messages)
        r_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')      #获取当前时间
        print(result_text)

        #封装请求数据和相应数据
        requestData['result_text'] = result_text
        requestData['r_timestamp'] = r_timestamp

        #构建序列化器对象
        serializer = UsersMessagesSerializers(data=requestData)
        #校验数据
        if serializer.is_valid(): #返回一个布尔值，所有字段都通过才返回true。serializer.validated_data        serializer.errors
            #数据校验通过，将数据插入数据库
            # Book.objects.create(**serializer.validated_data)
            serializer.save()  #存在返回对象

            return Response(serializer.data)
        else:
            #校验失败
            return Response(serializer.errors)
    def delete(self,request):       #不直接删除数据
        delete_amount = UsersMessages.objects.filter(userid=request.data['userid']).update(valid=0)
        return Response(delete_amount)


