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

LIMIT = int(os.getenv("LIMIT"))

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
            process_author(sub[2:])
        else:
            process_sub(sub)


def get_posts(page):
    new = [p for p in page.new(limit=LIMIT)]
    top = [p for p in page.top(limit=LIMIT, time_filter="month")]
    # hot = [p for p in page.hot(limit=LIMIT)]

    return new + top


def process_author(author):
    """Iterates over author posts."""
    user_page = reddit.redditor(author).submissions
    
    for post in get_posts(user_page):
        process_post(post)


def process_sub(sub):
    """Iterates over subreddit posts."""
    subreddit = reddit.subreddit(sub)

    for post in get_posts(subreddit):
        process_post(post)


def get_data(post):
    """Returns the data of a post."""
    data = vars(post)
    post_data = dict()

    for k in data.keys():
        if k[0] == "_" or k == "poll_data":
            continue

        if k in ["subreddit", "author"]:
            post_data[k] = str(data[k])
        else:
            post_data[k] = data[k]
    
    return post_data


def process_post(post):
    """Processes a single post."""
    print(f"{post.id} - {post.title}")

    post_data = get_data(post)

    all_files = download_post(post_data)
    save_data(post_data["id"], post_data, "/info/")
    save_data(post_data["id"], all_files, "/relations/")


def get_sha256(filename):
    """Gets the SHA256 of a file."""
    sha256_hash = hashlib.sha256()
    with open(filename, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096),b""):
            sha256_hash.update(byte_block)
        
    new_file = sha256_hash.hexdigest()
    if "." in filename:
        new_file += "." + filename.split('.')[-1]
    
    return new_file


def download_post(post):
    os.chdir("/pictures/_RedditPRAW/")

    uobd = "url_overridden_by_dest"
    if "url" not in post and uobd not in post:
        return
    
    url = uobd if uobd in post else "url"
    os.popen(f"gallery-dl -D . {post[url]}").read()
    time.sleep(1)

    all_files = []

    for dl_file in os.listdir():
        
        new_file = get_sha256(dl_file)
        all_files.append(new_file)

        # print(f"{post['id']} - {new_file[0:2]}/{new_file[2:4]}/{new_file[4:6]}/   {new_file[6:]}")
        # print(f"{post['id']} - {dl_file}")

        dirs = [new_file[di*2:di*2+2] for di in range(3)]
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


def save_data(post_id, post_data, directory):
    os.chdir(directory)

    post_id = post_id.zfill(8)
    dirs = [post_id[di*2:di*2+2] for di in range(2)]
    route = './'

    for dir_ in dirs:
        route += dir_ + '/'
        if not isdir(route):
            os.mkdir(route)

    json_data = dict()
    if f"{post_id[4:6]}.json" in os.listdir(route):
        with open(f"{route}{post_id[4:6]}.json") as read_file:
            json_data = json.load(read_file)

    json_data[post_id] = post_data

    with open(f"{route}{post_id[4:6]}.json", "w") as write_file:
        json.dump(json_data, write_file, indent=0, sort_keys=True)


if __name__ == "__main__":
    main()

