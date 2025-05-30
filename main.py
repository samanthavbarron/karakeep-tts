import datetime
import requests
import http.client
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import time
from tqdm import tqdm
from random import choice

import html2text
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from mutagen.easyid3 import EasyID3

load_dotenv()

@dataclass
class Config:
    media_path: Path = Path(os.getenv("MEDIA_PATH", "media"))
    elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "")
    karakeep_api_key: str = os.getenv("KARAKEEP_API_KEY", "")
    karakeep_api_host: str = os.getenv("KARAKEEP_API_HOST", "")
    bookmark_list_name: str = os.getenv("BOOKMARK_LIST_NAME", "Podcast")
    elevenlabs_model_id: str = os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5")
    sleep_interval: int = int(os.getenv("SLEEP_INTERVAL", 60))
    hc_url: str = os.getenv("HEALTHCHECK_URL", "")

CONFIG = Config()

elevenlabs = ElevenLabs(api_key=CONFIG.elevenlabs_api_key)

html_converter = html2text.HTML2Text()
html_converter.ignore_links = True
html_converter.ignore_emphasis = True
html_converter.ignore_images = True
html_converter.ignore_tables = True

media_path = Path(CONFIG.media_path)
media_path.mkdir(parents=True, exist_ok=True)

def karakeep_req(url: str, method: str = "GET") -> dict:
    conn = http.client.HTTPSConnection(CONFIG.karakeep_api_host, timeout=600)
    payload = ''
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {CONFIG.karakeep_api_key}',
    }
    conn.request(method, "/api/v1/" + url, payload, headers)
    res = conn.getresponse()
    data = res.read()
    response_str = data.decode("utf-8")
    try:
        return json.loads(response_str)
    except:
        return {}

@lru_cache()
def get_list_id_from_name(name: str) -> str:
    for l in karakeep_req("lists")["lists"]:
        if l.get("name", None) == name:
            return l.get("id")
    raise ValueError(f"List not found: {name}")

def get_bookmarks(list_name: str = CONFIG.bookmark_list_name):
    for bookmark in karakeep_req(f"lists/{get_list_id_from_name(list_name)}/bookmarks")["bookmarks"]:
        if _bm := Bookmark.from_dict(bookmark):
            yield _bm

def get_random_voice_id() -> str:
    voices = elevenlabs.voices.search(category="premade", page_size=50).voices
    return choice(voices).voice_id


@dataclass
class Bookmark:
    id: str
    title: str
    content: str
    url: str
    description: str | None = None
    
    def path(self, ext: str = "mp3") -> Path:
        return media_path / f"{self.title}.{ext}"

    @classmethod
    def from_dict(cls, data: dict):
        try:
            res = cls(
                id=data["id"],
                title=data["content"]["title"],
                url=data["content"]["url"],
                content=html_converter.handle(data["content"]["htmlContent"]),
                description=data["content"].get("description", None)
            )
            if res.title is None and res.description is not None:
                res.title = res.description
            
            return res
        except KeyError:
            return None
        
    def preamble(self) -> str:
        return f"""The following article is titled {self.title}. This is read by an automated voice."""
    
    def postamble(self) -> str:
        return f"""This article was titled {self.title}. Thanks for listening!"""
    
    def get_full_content(self) -> str:
        return f"{self.preamble()}\n\n{self.content}\n\n{self.postamble()}"
    
    def remove_from_list(self):
        karakeep_req(f"lists/{get_list_id_from_name(CONFIG.bookmark_list_name)}/bookmarks/{self.id}", method="DELETE")
    
    def process(self):
        if not self.path().exists():
            self.generate_audio()
        self.remove_from_list()
    
    def generate_audio(self):
        response = elevenlabs.text_to_speech.convert(
            text=self.get_full_content(),
            voice_id=get_random_voice_id(),
            model_id=CONFIG.elevenlabs_model_id,
            output_format="mp3_44100_128",
        )
        with open(self.path(), "wb") as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)

            audio = EasyID3(str(self.path()))
            audio["title"] = self.title
            audio["date"] = datetime.datetime.now().isoformat()
            audio.save()

def ping_hc(failure: bool = False):
    if not CONFIG.hc_url:
        return  # No healthcheck URL configured

    hc_url = CONFIG.hc_url.rstrip("/")
    if failure:
        hc_url = hc_url + "/fail"

    try:
        requests.get(CONFIG.hc_url, timeout=10)
    except requests.RequestException as e:
        print("Ping failed: %s" % e)


if __name__ == "__main__":
    try:
        while True:
            for bookmark in tqdm(list(get_bookmarks())):
                try:
                    bookmark.process()
                except Exception as e:
                    print(f"Error processing bookmark {bookmark.id}: {e}")
            ping_hc()
            time.sleep(CONFIG.sleep_interval)
    except Exception as e:
        if isinstance(e, KeyboardInterrupt):
            print("Process interrupted by user.")
        else:
            print(f"An error occurred: {e}")
            ping_hc(failure=True)
            raise e