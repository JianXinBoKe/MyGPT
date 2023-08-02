import os
import threading

import openai
import random
import time

# 存储不同 API key 的字典
keys = {
    '魏建新': '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',
    '高浩哲': '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',
    '杨名 ':  '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',
    '史鸿涛': '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',
    '张钊源': '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',
}

# 设置代理，访问 OpenAI API
# os.environ["HTTP_PROXY"] = 'http://127.0.0.1:9910'
# os.environ["HTTPS_PROXY"] = 'http://127.0.0.1:9910'

def get_chat_response(messages):
    while True:
        try:
            # 生成基于当前时间和线程 ID 的随机种子
            timestamp = int(time.time())
            thread_id = threading.get_ident()
            random_seed = timestamp * thread_id
            # 使用不同的种子调用 random.choice 函数，随机选择一个 API key
            # random.seed(random_seed)
            # openai.api_key = random.choice(list(keys.values()))
            openai.api_key = keys[list(keys.keys())[random_seed % len(keys)]]
            # print(openai.api_key)

            # 向 OpenAI API 发送请求，获取聊天回复
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # 使用的 GPT-3.5 模型
                messages=messages,
                max_tokens=1600,  # 最大生成 token 数
                stop=None,          #生成的回答将不会受到任何特定符号的限制，可以自由地生成长度更长的回答
                temperature=1.0,  # 温度参数，控制聊天回复的多样性
                n=1,               #生成的回答数量
                top_p=0.9,  # 使用 top-p sampling 算法，控制生成 token 的概率分布
                frequency_penalty=0.2,  # 频率惩罚项，控制生成 token 的多样性
                presence_penalty=0.2,  # 存在惩罚项，控制生成 token 的多样性
            )

            # 返回聊天回复的内容
            return response.choices[0].message.content.strip()

        except openai.error.RateLimitError:
            # 如果触发了速率限制，等待一段时间后重试
            print("OpenAI API error occurred. Retrying in 10 seconds...")
            time.sleep(60/(len(keys)*3))

if __name__ == '__main__':
    # 构造一个包含用户消息的列表
    message = [{"role": "user", "content": "你是谁？"}]
    # 调用 get_chat_response 函数获取聊天回复
    result = get_chat_response(message)
    # 输出聊天回复
    print('********************')
    print(result)
    print('********************')