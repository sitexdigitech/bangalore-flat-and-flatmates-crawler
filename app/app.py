import time
import logging
from typing import Union
from crawler import Crawler
from processor import Processor
from db import FlatAndFlatmatesDatabase
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig(
    level=logging.INFO,
    filename="app.log",
    format="%(asctime)s - %(levelname)s - %(filename)s:%(funcName)s:%(threadName)s:%(lineno)d - %(message)s",
    filemode="w",
)


def fetch_latest_posts_from_group(group_id: Union[str, int], pages: int = 1):
    logging.info(f"Fetching latest posts from {group_id}")
    posts = crawler.crawl_posts_from_group(group_id, pages)
    logging.info(f"Found {len(posts)} posts")
    logging.debug(posts)
    posts = processor.process(posts)
    logging.info("Inserting posts into database")
    for post in posts:
        db.add_new_post_entry(post)


def fetch_latest_posts():
    logging.info(f"Fetching new posts from groups")
    group_ids = SEARCH_CONFIG.get("groups", [])
    num_pages = SEARCH_CONFIG.get("pages", 4)
    if not SEARCH_CONFIG.get("multithreaded", False):
        for group_id in group_ids:
            fetch_latest_posts_from_group(group_id, num_pages)
            time.sleep(10)
    else:
        num_group_ids = len(group_ids)
        num_pages_iterable = [num_pages] * num_group_ids
        with ThreadPoolExecutor(max_workers=num_group_ids) as executor:
            executor.map(
                fetch_latest_posts_from_group,
                group_ids,
                num_pages_iterable,
            )


if __name__ == "__main__":
    logging.info("Starting Facebook Group Crawler")

    processor = Processor()
    SEARCH_CONFIG = processor.load_config("conf/search_config.json")
    logging.debug(f"Loaded search_config: {SEARCH_CONFIG}")

    db = FlatAndFlatmatesDatabase()
    crawler = Crawler(SEARCH_CONFIG.get("crawler_options", Crawler.DEFAULT_OPTIONS))

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        fetch_latest_posts, "interval", minutes=SEARCH_CONFIG.get("interval", 20)
    )

    logging.info("Starting scheduler for fetching new posts")
    scheduler.start()

    try:
        while True:
            time.sleep(1e4)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Shutting down Facebook Group Crawler")
        scheduler.shutdown()
