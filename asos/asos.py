from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import json
import os
import threading
import re
import enum

lock = threading.Lock()

class FileManager:

    @staticmethod
    def save_to_file(filename, values):
        
        file_path = f"{filename}.json"
        with lock:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {filename: []}

            if values not in data[filename]:
                data[filename].append(values)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)

    @staticmethod
    def load_from_file(filename):
        file_path = f"{filename}.json"
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {filename: []}

    @staticmethod
    def is_duplicate(filename, value):
        data = FileManager.load_from_file(filename).get(filename, [])
        return value in data

    @staticmethod
    def mark_as_processed(filename, value):
        FileManager.save_to_file(filename, value)


class RequestType(enum.Enum):
    GET_DATA = 0
    BUY_THE_LOOK = 1

class Asos(threading.Thread):
    session = requests.Session()

    def __init__(self, thread_id, request_type, thread_url):
        super().__init__()
        self.thread_id = thread_id
        self.request_type = request_type
        self.thread_url = thread_url

    def requests_url(self, url):
        headers = {
            "User-Agent": "PostmanRuntime/7.40.0",
        }
        retry_strategy = Retry(
            total=7,
            status_forcelist=[429, 500, 502, 503, 504, 400],
            allowed_methods=["GET", "POST"],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        try:
            response = session.get(url, headers=headers)
            return response
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            FileManager.save_to_file("failed_requests", url)
            return None

    def calculate_item_count(self, url):
        response = self.requests_url(url)
        if response:
            return int(json.loads(response.content).get("itemCount", 0))
        return 0


    def get_data(self,url):
        cid=url.split("?")[0].split("/")[-1]

        for item_count in range(0,self.calculate_item_count(url),200):
            url=f"https://www.asos.com/api/product/search/v2/categories/{cid}?channel=desktop-web&country=US&currency=USD&keyStoreDataversion=mhabj1f-41&lang=en-US&limit=200&offset={item_count}&rowlength=4&store=US&tstSearchSponsoredProducts=true"
            response=self.requests_url(url)
            if response:
              FileManager.save_to_file("data", json.loads(response.content))


    def get_buy_the_look(self, url):
        response = self.requests_url(url)
        if  response:
            pattern = r'\{"heroLookUrl":"https:\/\/api\.asos\.com\/product\/catalogue\/v4\/productlooks\?lookIds=\d+&store=[A-Za-z]{2,3}"\}'
            matches = re.findall(pattern, response.text)
            hero_url = json.loads(matches[0]).get("heroLookUrl") if matches else None
            if hero_url:
                hero_response = self.requests_url(hero_url)
                if hero_response:
                    FileManager.save_to_file("by_the_look", json.loads(hero_response.content))


    def dispatch(self):
        dispatch_map = {
            RequestType.GET_DATA: self.get_data,
            RequestType.BUY_THE_LOOK: self.get_buy_the_look,
        }
        method = dispatch_map.get(self.request_type, lambda x: None)
        method(self.thread_url)

    def run(self):
        self.dispatch()
