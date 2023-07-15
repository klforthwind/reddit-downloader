from dotenv import load_dotenv
from datetime import datetime
from os.path import isfile
from os.path import isdir
import logging as logger
import inspect
import hashlib
import json
import praw
import time
import sys
import os

load_dotenv()

LIMIT = int(os.getenv("LIMIT"))

logger.basicConfig(
    format='%(asctime)s %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p %Z',
    level=logger.INFO
)

reddit = praw.Reddit(
    client_id = os.getenv('client'),
    client_secret = os.getenv('secret'),
    username = os.getenv('reddit_user'),
    password = os.getenv('reddit_pass'),
    user_agent = 'ForthBot/0.1.4',
)

def main():
    logger.info(f"App is up and running!")

    while True:
        subscribed = list(reddit.user.subreddits(limit=None))
        subreddits = sorted(list(map(lambda s: s.display_name, subscribed)))

        for sub in subreddits:
            logger.info(f"Processing {sub}!")

            if sub[0:2] == "u_":
                process_author(sub[2:])
            else:
                process_sub(sub)

        time.sleep(600)

    logger.info(f"App is finished and exiting!")


def get_posts(page):
    new = [p for p in page.new(limit=LIMIT)]
    # top = [p for p in page.top(limit=LIMIT, time_filter="month")]
    # hot = [p for p in page.hot(limit=LIMIT)]

    # return new + top
    return new


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
    if post_exists(post.id):
        return

    logger.info(f"{post.id} - {post.title}")

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

def download_from_archived(post):
    proc_files = []
    data = post

    parents = "crosspost_parent_list"
    if parents in data and len(data[parents]):
        data = data["crosspost_parent_list"][0]

    if "gallery_data" in data and "media_metadata" in data and data["gallery_data"] is not None:
        logger.info(f"MediaMetadata - Downloading")
        order = list(map(lambda x: x["media_id"], data["gallery_data"]["items"]))

        for o_id in order:
            try:
                if data["media_metadata"][o_id]["status"] != "failed":
                    source = data["media_metadata"][o_id]["s"]
                    key = "u"
                    if "gif" in source:
                        key="gif"
                    elif "mp4" in source:
                        key="mp4" 
                    url = source[key].replace("&amp;", "&")
                    os.popen(f'gallery-dl "{url}" -D . ').read()
                    for f in os.listdir():
                        if f not in proc_files:
                            proc_files.append(f)
            except:
                pass
    return proc_files


def download_post(post):
    os.chdir("/pictures/_RedditPRAW2/")

    uobd = "url_overridden_by_dest"
    if "url" not in post and uobd not in post:
        return
    
    url_key = uobd if uobd in post else "url"
    url = post[url_key].replace("&amp;", "&")
    # agent = "-o 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0'"
    if 'v.redd.it' in url:
        os.popen(f'youtube-dl "{url}"').read()
    else:
        os.popen(f'gallery-dl "{url}" -D . --range 1-4096 ').read()
    time.sleep(1)

    all_files = []
    proc_files = []

    if len(os.listdir()) == 0 and ".gif" not in url and ".mp4" not in url:
        proc_files = download_from_archived(post)
    if len(os.listdir()) == 0 and "preview" in post:
        try:
            url = post["preview"]["images"][0]["source"]["url"].replace("&amp;", "&")
            os.popen(f'gallery-dl "{url}" -D . ').read()
            for f in os.listdir():
                if f not in proc_files:
                    proc_files.append(f)
        except:
            pass

    if len(proc_files) == 0:
        proc_files = sorted(os.listdir())

    for dl_file in proc_files:
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


def post_exists(post_id):
    os.chdir("/relations/")
    post_id = post_id.zfill(8)
    dirs = [post_id[di*2:di*2+2] for di in range(2)]
    route = './'

    for dir_ in dirs:
        route += dir_ + '/'
        if not isdir(route):
            return False

    if not isfile(f"{route}{post_id[4:6]}.json"):
        return False

    with open(f"{route}{post_id[4:6]}.json") as read_file:
        json_data = json.load(read_file)
        return post_id in json_data


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
    if isfile(f"{route}{post_id[4:6]}.json"):
        with open(f"{route}{post_id[4:6]}.json") as read_file:
            json_data = json.load(read_file)

    json_data[post_id] = post_data

    with open(f"{route}{post_id[4:6]}.json", "w") as write_file:
        json.dump(json_data, write_file, sort_keys=True)


if __name__ == "__main__":
    main()

