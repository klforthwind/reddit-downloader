from dotenv import load_dotenv
from datetime import datetime
from os.path import isfile
from os.path import isdir
import inspect
import hashlib
import json
import praw
import time
import sys
import os

load_dotenv()

reddit = praw.Reddit(
    client_id = os.getenv('client'),
    client_secret = os.getenv('secret'),
    username = os.getenv('reddit_user'),
    password = os.getenv('reddit_pass'),
    user_agent = 'ForthBot/0.1.4',
)

submission = reddit.submission(id="")

print(submission.id)
print(submission.title)

data = vars(submission)

for k in data.keys():
    print(f"{k} - {data[k]}")


