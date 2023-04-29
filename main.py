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

def main():
    subscribed = list(reddit.user.subreddits(limit=None))
    subreddits = sorted(list(map(lambda s: s.display_name, subscribed)))

    for sub in subreddits:
        print(f"Processing {sub}!")

        if sub[0:2] == "u_":
            process_author(sub)
        else:
            process_sub(sub)


def get_posts(page):
    new = [p for p in page.new(limit=10)]
    top = [p for p in page.top(limit=10, time_filter="month")]
    # hot = [p for p in page.hot(limit=10)]

    return new + top


def process_author(author):
    user_page = reddit.redditor(author).submissions
    
    for post in get_posts(user_page):
        process_post(post)


def process_sub(sub):
    subreddit = reddit.subreddit(sub)

    for post in get_posts(subreddit):
        process_post(post)


def process_post(post):
    print(f"{post.id} - {post.title}")

    data = vars(post)
    post_data = dict()

    for k in data.keys():
        if k[0] != "_" and k != "poll_data":
            if k in ["subreddit", "author"]:
                post_data[k] = str(data[k])
            else:
                post_data[k] = data[k]

    download_post(post_data)
    save_post(post_data)


def download_post(post):
    if "url" not in post and "url_overridden_by_dest" not in post:
        return
    
    url = "url_overridden_by_dest" if "url_overridden_by_dest" in post else "url"

    os.chdir("/pictures/_RedditPRAW/")

    print(post[url])

    os.popen(f"gallery-dl -D . {post[url]}").read()
    time.sleep(1)

    all_files = []

    for dl_file in os.listdir():
        sha256_hash = hashlib.sha256()
        with open(dl_file, "rb") as f:
            # Read and update hash string value in blocks of 4K
            for byte_block in iter(lambda: f.read(4096),b""):
                sha256_hash.update(byte_block)
            
        new_file = sha256_hash.hexdigest()
        if "." in dl_file:
            new_file += "." + dl_file.split('.')[-1]

        all_files.append(new_file)

        # print(f"{post['id']} - {new_file[0:2]}/{new_file[2:4]}/{new_file[4:6]}/   {new_file[6:]}")
        # print(f"{post['id']} - {dl_file}")

        dirs = []
        for di in range(3):
            dirs.append(new_file[di*2:di*2+2])

        route = '../'

        for dir_ in dirs:
            route += dir_ + '/'
            if not isdir(route):
                os.mkdir(route)

        if not isfile(f'"{route}{new_file[2*len(dirs):]}"'):
            os.popen(f'cp "./{dl_file}" "{route}{new_file[2*len(dirs):]}"').read()
        os.popen(f'rm "./{dl_file}"').read()
    
    if len(os.listdir()):
        raise Exception

    return all_files

def save_post(post_data):
    os.chdir("/info/")

    post_id = post_data["id"].zfill(8)

    dirs = [post_id[di*2:di*2+2] for di in range(2)]

    route = './'

    for dir_ in dirs:
        route += dir_ + '/'
        if not isdir(route):
            os.mkdir(route)

    if f"{post_id[4:6]}.json" in os.listdir(route):
        with open(f"{route}{post_id[4:6]}.json") as read_file:
            json_data = json.load(read_file)
    else:
        json_data = dict()

    json_data[post_id] = post_data

    with open(f"{route}{post_id[4:6]}.json", "w") as write_file:
        json.dump(json_data, write_file)


if __name__ == "__main__":
    main()

