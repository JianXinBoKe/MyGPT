# import requests
# import json
#
# url = 'http://43.156.51.51:80/messages/'
# headers = {'Content-Type': 'application/json'}
# data = {
#     "userid": "2",
#     "username": "John Doe",
#     "question_text": "你是谁？",
#     "q_timestamp": "2023-03-28T15:26:33.045000+08:00"
# }
# response = requests.post(url, headers=headers, data=json.dumps(data))
# print(response.status_code)
# print(response.text)

import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(verbose=True)
print(os.getenv('MYSQL_USER'))