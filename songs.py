# songen.py
############################################################################
from openai import OpenAI  # openai sdk
from dotenv import load_dotenv  # für zugriff auf .env
import requests as req  # für http requests
import os, json, time, re  # built-ins

############################################################################
PROMPTNAME = "meta"  # dateiname der prompt (ohne typendung)
STYLENAME = "rap"  # dateiname der songinfo (ohne typendung)
############################################################################
load_dotenv()  # .env inhalt in script verfügbar machen


############################################################################

def writeFile(path: str, data):  # funktion um datei zu schreiben
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)  # ordner erstellen, falls nicht vorhanden
    with open(path, "w", encoding="utf-8") as f:  # sicherer mit with open() via buffer stream
        if path.endswith(".json"):  # wenn ziel eine json, dann
            json.dump(data, f, indent=4, ensure_ascii=False)  # via json package formatieren
        else:
            f.write(data)  # sonst datei regulär schreiben
    print(f"file saved to: {path}")  # success print für saved file


# ---------------------------------------------------------------------------

def readFile(path: str):  # funktion um datei zu lesen
    with open(path, "r", encoding="utf-8") as f:  # sicherer mit with open() via buffer stream
        if path.endswith(".json"):
            return json.load(f)  # wenn json dann json parsen und returnen
        else:
            return f.read()  # sonst datei regulär lesen und returnen


############################################################################

class Chat:
    # -----------------------------------------------------------------------
    def __init__(self):  # konstruktor
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # openai client via sdk als attribut

    # -----------------------------------------------------------------------
    def get_response(self, pmt, web=False):  # funktion um openai completion zu callen
        params = {  # params vordefinieren
            "model": "gpt-5-mini",  # model auswahl
            "input": pmt,  # metaprompt + songinfo json als string
        }
        if web: params["tools"] = [{"type": "web_search"}]  # websearch tool nutzen, wenn true
        return self.client.responses.create(**params).output_text  # openai responses api callen

    # -----------------------------------------------------------------------
    def get_prompt(self, path, data, meta=True, con=True):  # funktion um lyrics prompt zu bauen
        p: str = readFile(path)  # promptdatei lesen
        keys = re.findall(r"__(.*?)__", p)  # placeholder keys aus prompt lesen
        for k in keys: p = p.replace(f"__{k}__", str(data.get(k,
                                                              "")))  # alle keys in prompt durch values ersetzen
        p = p + str(data) if con else p  # daten konkatentieren, wenn True
        if meta:
            return self.get_response(p, True)  # wenn metaprompt: dann lyricsprompt via openai
        else:
            return p  # sonst: direkt ddie fertige promot returnen


############################################################################

class Song:  # klasse für suno client
    # -----------------------------------------------------------------------
    def __init__(self):  # konstruktor
        self.api_key = os.getenv("SUNO_API_KEY")  # apikey als attribut
        self.base = "https://api.acedata.cloud/suno"  # acedata api endpoint
        self.hd = {  # post equest header
            "accept": "application/json",  # lt. provider
            "authorization": f"Bearer {self.api_key}",  # apykey für auth
        }

    # -----------------------------------------------------------------------
    def post(self, url, data, tm=60):  # method for post request
        resp = req.post(url, json=data, headers=self.hd, timeout=tm)
        resp.raise_for_status()  # error wenn status nicht 200
        return resp.json()  # return response as dict

    # -----------------------------------------------------------------------
    def generate(self, data, maxtime):  # song generation tool von suno callen
        return self.post(f"{self.base}/audios", data, maxtime)  # richtige daten via most post method

    # -----------------------------------------------------------------------
    def retrieve(self, task_id):  # status einer generation task abfragen
        payload = {"action": "retrieve", "id": task_id}  # payload bauen
        return self.post(f"{self.base}/tasks", payload)  # richtige daten via most post method

    # -----------------------------------------------------------------------
    def download(self, url):  # sond als binary von url herunterladen
        fetch = req.get(url, timeout=120)  # via get method
        fetch.raise_for_status()  # error wenn status nicht 200
        return fetch.content  # benötigte daten returnen


############################################################################

def get_songs(sunodata, lyrics):  # suno song generation vorbereiten
    suno = Song()  # suno object instanzieren
    maxtime, pause = 15 * 60, 20  # in secs: maximale dauer und pause zwischen pause
    # -----------------------------------------------------------------------
    payload = {  # payload für post request bauen
        "action": "generate",  # post method for generation
        "model": sunodata["model"],  # generation model (chirp-v5)
        "prompt": sunodata["prompt"],  # unsere suno prompt aus songinfo.json
        "lyric": lyrics,  # die con openai generirte lyrics prompt
        "custom": sunodata["custom"],  # true weil mit custom lyrics
        "instrumental": sunodata["instrumental"],  # false weil kein reine instrumental sondern mit lyrics
        "title": sunodata["title"],  # title aus songinfo.json
        "style": sunodata["style"],  # wie prompt (optional)
        "vocal_gender": sunodata["vocal_gender"],  # gender aus songinfo.json
    }
    # -----------------------------------------------------------------------
    print("starting song creation ...")  # info über prozessstart
    task = suno.generate(payload, maxtime)  # song gen starten und task objekt holen
    if not task.get("success"): raise Exception(task)  # wenn keine task dann abbruch
    task_id, sdata = task.get("task_id"), task.get("data")  # task id und songs data holen
    if not sdata: raise Exception(sdata)  # wenn keine songdaten dann abbruch
    sids = {data.get("id") for data in sdata if data.get("id")}  # set mit song ids bauen
    # -----------------------------------------------------------------------
    retry = maxtime // pause  # max anzahl der abrufe ermitteln
    while retry > 0:  # loop solange noch retries übrig
        try:
            retry -= 1  # je loop step einen retry abziehen
            task: dict = suno.retrieve(task_id)  # aktuelle task daten abrufen
            data: list[dict] = task.get("response").get("data")  # aktuelle liste aus dicts mit songdaten
            for d in data:  # durch songs loopen
                url, sid = d.get("audio_url"), d.get("id")  # url und song id holen
                if not url or not sid or not sids: continue  # wenn grds. daten fehlern, dann next loopstep
                song = suno.download(url)  # song downloaden und cachen
                with open(f"songs/{sid}.mp3", "wb") as f:
                    f.write(song)  # song als mp3 abspeichern
                writeFile(f"lyrics/{sid}.txt", lyrics)  # lyrics mit song id als dateinamen abspeichern
                sids.discard(sid)  # song aus sid liste löschen, wenn runtergeladen
                print(f"saved: songs/{sid}.mp3")  # success info printen
        except:
            pass  # kein print weil im loop
        if not sids: return  # beenden wenn keine songs übrig
        time.sleep(pause)  # kleine pause vor next request


############################################################################

def run(promptname, stylename):  # main function

    chat = Chat()  # chat objekt instanziieren
    meta = "meta" in promptname  # True ? -> call metaprompt logik

    print("get songinfo ...")  # status info
    style: dict = readFile(f"styles/{stylename}.json")  # songinfo lesen
    sunodata = style.get("suno")  # sunodata separat merken
    style.pop("suno", "")  # songinfo ohne sunodata nutzen

    print("get prompt ...")  # status info
    prompt = chat.get_prompt(f"prompts/{promptname}.md", style, meta)  # lyricsprompt holen
    writeFile("temp/prompt.txt", prompt)  # sicherheitskopie speichern

    print("get lyrics ...")  # status info
    lyrics = chat.get_response(prompt, web=not meta)  # openai call durchführen
    writeFile("temp/lyrics.txt", lyrics)  # sicherheitskopie speichern

    print("get song ...")  # status info
    get_songs(sunodata, lyrics)  # song kreieren und downloaden


############################################################################

if __name__ == "__main__":  # execution guard
    print(run(PROMPTNAME, STYLENAME))  # call main function






