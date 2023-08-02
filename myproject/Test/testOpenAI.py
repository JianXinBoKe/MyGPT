import json
import threading
import requests
from multiprocessing import Process, Queue
from openaigpt.aigpt import get_chat_response

# 全局线程和进程数目：[进程,线程]
progress_thread = [2, 3]


def testapp(q,question):
    url = 'http://43.156.51.51:80/messages/'
    headers = {'Content-Type': 'application/json'}
    data = {
        "userid": "2",
        "username": "John Doe",
        "question_text": question,
        "q_timestamp": "2023-03-28T15:26:33.045000+08:00"
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    # 将字符串转换为字典对象
    dict_data = json.loads(response.text)
    result = dict_data['result_text']
    q.put(result)

def testGPT(q,question):
    message = [{"role": "user", "content": question}]
    result = get_chat_response(message)
    q.put(result)

# 定义一个启动线程的函数
def start_threads(q, param):
    threads = []
    global progress_thread
    for i in range(progress_thread[1]):
        t = threading.Thread(target=testapp, args=(q, param))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()


if __name__ == '__main__':
    # 定义一个空列表来存储所有进程对象
    processes = []
    # 定义一个队列用于存储子进程的返回值
    q = Queue()

    # 循环创建多个进程
    for i in range(progress_thread[0]):
        p = Process(target=start_threads, args=(q, '你好吗'))
        # p = Process(target=testapp, args=(q, '你好'))
        processes.append(p)
        p.start()

    # 等待所有子进程执行完毕
    for p in processes:
        p.join()

    # 从队列中获取所有子进程的返回值
    results = []
    while not q.empty():
        results.append(q.get())
        print(q.get())

    # 打印所有子进程的返回值
    print(len(results) , ':' , results)





