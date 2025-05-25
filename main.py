import datetime
import http.client

from dataclasses import dataclass
from pathlib import Path
from random import choice
import html2text
import json
from mutagen.easyid3 import EasyID3
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import os
from rich import print

load_dotenv()

elevenlabs = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

h = html2text.HTML2Text()
h.ignore_links = True
h.ignore_emphasis = True
h.ignore_images = True
h.ignore_tables = True

def karakeep_req(url: str):
    conn = http.client.HTTPSConnection(os.getenv("KARAKEEP_API_HOST", "api.karakeep.com"))
    payload = ''
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {os.getenv("KARAKEEP_API_KEY")}'
    }
    conn.request("GET", "/api/v1/" + url, payload, headers)
    res = conn.getresponse()
    data = res.read()
    response_str = data.decode("utf-8")
    return json.loads(response_str)

def get_list_id_from_name(name: str) -> str:
    for l in karakeep_req("lists")["lists"]:
        if l.get("name", None) == name:
            return l.get("id")
    raise ValueError(f"List not found: {name}")

media_path = Path(os.getenv("MEDIA_PATH", "media"))
media_path.mkdir(parents=True, exist_ok=True)

@dataclass
class Bookmark:
    id: str
    title: str
    content: str
    url: str
    description: str | None = None
    
    def path(self, ext: str = "mp3") -> Path:
        return media_path / f"{self.id[:8]}.{ext}"

    @classmethod
    def from_dict(cls, data: dict):
        try:
            res = cls(
                id=data["id"],
                title=data["content"]["title"],
                url=data["content"]["url"],
                content=h.handle(data["content"]["htmlContent"]),
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
    
    def generate_audio(self):
        if self.path().exists():
            return
        response = elevenlabs.text_to_speech.convert(
            text=self.get_full_content(),
            voice_id=get_random_voice_id(),
            model_id="eleven_turbo_v2_5",
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

def get_bookmarks(list_name: str = "Podcast"):
    for bookmark in karakeep_req(f"lists/{get_list_id_from_name(list_name)}/bookmarks")["bookmarks"]:
        if _bm := Bookmark.from_dict(bookmark):
            yield _bm

def get_random_voice_id() -> str:
    voices = elevenlabs.voices.search(category="premade", page_size=50).voices
    return choice(voices).voice_id

if __name__ == "__main__":
    for bookmark in get_bookmarks("Podcast"):
        print(f"Title: {bookmark.title}")
        bookmark.generate_audio()