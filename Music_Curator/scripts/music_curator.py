#!/usr/bin/env python3
"""
music_curator.py - Automated Music Tag & Album Art Curator
Handles:
  1. Album Art Curation:
     - Check MP3, FLAC, M4A for embedded cover art
     - If art exists in tag: do nothing (preserve)
     - If art missing:
       a) Check for local 'cover.jpg' / 'Cover.jpg' in folder and embed
       b) If no cover.jpg: search internet (iTunes, Deezer, CoverArtArchive) using
          Band and Album (from tags or folder name), download high-res art,
          save as cover.jpg, and embed into file tags
  2. Intelligent Genre Classification & Tagging:
     - Automatically guesses and assigns genre from band name, album, and tags:
       1) Hard Rock (Metal, Heavy Metal, Death/Black/Thrash Metal, Prog Metal, Blues Rock)
       2) Rock (Rock, Alternative, Country, Indie, Folk, Pop-Rock, Santana, Florence + the Machine)
       3) Female (Solo female singers, including Norah Jones, Eva Cassidy, Ann Wilson, etc.)
       4) Progressive Rock (Prog Rock, Symphonic Prog, Space Rock, Neo-Prog)
       5) Christmas (Christmas and Holiday albums/tracks)
       6) Jazz (Jazz, Bebop, Jazz Fusion, Vocal Jazz, Smooth Jazz)
       7) Latina (Spanish / Latino rhythm, Flamenco, etc.)
     - Also supports setting a custom fixed genre (e.g. --genre "Hard Rock")
"""

import os
import sys
sys.stdout.reconfigure(encoding="utf-8")
import re
import json
import argparse
import urllib.request
import urllib.parse
from pathlib import Path
from collections import Counter

# Auto-locate mutagen from virtual environments if not in system python
try:
    import mutagen
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC, Picture
    from mutagen.mp4 import MP4
    from mutagen.id3 import ID3, APIC, TCON, ID3NoHeaderError
except ImportError:
    user_home = Path.home()
    candidate_venv_paths = [
        str(user_home / ".gemini" / "antigravity" / "scratch" / ".venv" / "Lib" / "site-packages"),
        str(user_home / ".venv" / "Lib" / "site-packages"),
        os.path.expandvars(r"%APPDATA%\Python\Python313\site-packages"),
        os.path.expandvars(r"%APPDATA%\Python\Python312\site-packages"),
        os.path.expandvars(r"%APPDATA%\Python\Python311\site-packages"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python313\Lib\site-packages"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python312\Lib\site-packages"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python311\Lib\site-packages"),
    ]
    for vp in candidate_venv_paths:
        if os.path.isdir(vp) and vp not in sys.path:
            sys.path.insert(0, vp)
            break
    try:
        import mutagen
        from mutagen.mp3 import MP3
        from mutagen.flac import FLAC, Picture
        from mutagen.mp4 import MP4
        from mutagen.id3 import ID3, APIC, TCON, ID3NoHeaderError
    except ImportError:
        print("Error: 'mutagen' library is required. Please install it using: pip install mutagen", file=sys.stderr)
        sys.exit(1)

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".m4a"}

# --- Genre Classification Rules & Knowledge Base ---

CHRISTMAS_PATTERNS = [
    r"\bchristmas\b", r"\bxmas\b", r"\bnoel\b", r"\bnoël\b",
    r"\bsanta\b", r"\bho ho ho\b", r"\bcarols?\b", r"\bnativity\b",
    r"\bjingle bells\b", r"\bwinter wonderland\b", r"\bmerry christmas\b",
    r"\bholiday (hits|jam|album|season|classics|collection|favorites|cheer|greetings)\b"
]

LATINA_PATTERNS = [
    r"\blatina\b", r"\blatino\b", r"\blatin\b", r"\bflamenco\b", r"\bsalsa\b",
    r"\bbossa nova\b", r"\btango\b", r"\brumba\b", r"\bsamba\b", r"\bcumbia\b",
    r"\bbachata\b", r"\bmariachi\b", r"\breggaeton\b"
]

JAZZ_PATTERNS = [
    r"\bjazz\b", r"\bbebop\b", r"\bhard bop\b", r"\bcool jazz\b",
    r"\bsmooth jazz\b", r"\bjazz fusion\b", r"\bbig band\b", r"\bswing\b",
    r"\bjazz-rock\b", r"\bacid jazz\b", r"\bmodal jazz\b"
]

PROG_PATTERNS = [
    r"\bprogressive rock\b", r"\bprog rock\b", r"\bprog-rock\b", r"\bspace rock\b",
    r"\bsymphonic rock\b", r"\bneo-prog\b", r"\bkrautrock\b", r"\bcanterbury scene\b",
    r"\bart rock\b", r"\bpsychedelic space rock\b"
]

HARD_ROCK_PATTERNS = [
    r"\bmetal\b", r"\bheavy metal\b", r"\bhard rock\b", r"\bhard-rock\b",
    r"\bblues rock\b", r"\bblues-rock\b", r"\bstoner\b", r"\bthrash\b",
    r"\bdeath metal\b", r"\bblack metal\b", r"\bpower metal\b", r"\bdoom metal\b",
    r"\bgothic metal\b", r"\bgrindcore\b", r"\bmetalcore\b", r"\bdeathcore\b",
    r"\bnu metal\b", r"\bnu-metal\b", r"\bsludge\b", r"\bspeed metal\b",
    r"\bglam metal\b", r"\bmelodic metal\b", r"\bprogressive metal\b",
    r"\bprog metal\b", r"\bheavy\b", r"\bnwobhm\b", r"\bрок/металл\b",
    r"\bметал\b", r"\bметалл\b", r"\bхард-рок\b", r"\bdeath\b", r"\bheavy/speed\b",
    r"\bheavy/stoner\b", r"\bpost-grunge\b", r"\bgrunge\b"
]

KNOWN_LATINA_ARTISTS = {
    "buena vista social club", "paco de lucia", "paco de lucía", "gipsy kings",
    "rodrigo y gabriela", "vicente amigo", "los lobos", "manu chao", "julio iglesias",
    "enrique iglesias", "rosalia", "rosalía", "gloria estefan", "celia cruz", "tito puente",
    "compay segundo", "ibrahim ferrer", "omara portuondo", "ruben blades", "rubén blades",
    "antonio carlos jobim", "astrud gilberto", "joao gilberto", "joão gilberto",
    "caetano veloso", "gilberto gil", "charly garcia", "soda stereo", "heroes del silencio",
    "héroes del silencio", "fito paez", "andres calamaro", "marcello de angelis", "andrea bocelli"
}

KNOWN_JAZZ_ARTISTS = {
    "miles davis", "john coltrane", "dave brubeck", "bill evans", "chet baker",
    "thelonious monk", "charlie parker", "duke ellington", "duke ellington & john coltrane",
    "count basie", "louis armstrong", "charles mingus", "herbie hancock", "chick corea",
    "wayne shorter", "pat metheny", "pat metheny group", "keith jarrett", "al di meola",
    "mahavishnu orchestra", "weather report", "return to forever", "stanley clarke",
    "marcus miller", "lee ritenour", "fourplay", "spyro gyra", "yellowjackets",
    "snarky puppy", "casiopea", "t-square", "diana krall", "esperanza spalding",
    "george benson", "wes montgomery", "grant green", "kenny burrell", "django reinhardt",
    "stephane grappelli", "avishai cohen", "brad mehldau", "hiromi", "kamasi washington",
    "badbadnotgood", "john scofield", "bill frisell", "allan holdsworth", "gogo penguin",
    "frank sinatra", "candy dulfer", "david a. stewart feat. candy dulfer", "david a. stewart",
    "richard marx"
}

KNOWN_FEMALE_SOLO = {
    "adele", "alanis morissette", "alela diane", "alison krauss", "amy winehouse",
    "angel olsen", "ani difranco", "ann wilson", "anneke van giersbergen", "annie lennox",
    "avril lavigne", "beth gibbons", "beth hart", "billie eilish", "björk", "bjork",
    "bonnie raitt", "brandi carlile", "carly simon", "carole king", "cassandra wilson",
    "cat power", "chelsea wolfe", "chrissie hynde", "courtney barnett", "cyndi lauper",
    "dido", "dolores o'riordan", "dora jar", "dusty springfield", "ella fitzgerald",
    "ella langley", "emiliana torrini", "emma ruth rundle", "emmylou harris", "fiona apple",
    "grace potter", "grace slick", "gwen stefani", "hayley williams", "janis joplin", "jewel",
    "joan baez", "joan jett", "joan osborne", "joni mitchell", "joss stone", "judie tzuke",
    "judy collins", "julie christmas", "kacey musgraves", "kate bush", "kate rusby",
    "keren ann", "kt tunstall", "lady gaga", "lana del rey", "laura marling", "laura nyro",
    "linda ronstadt", "lisa gerrard", "lita ford", "lorde", "loreena mckennitt",
    "lucinda williams", "maggie rogers", "marianne faithfull", "marissa nadler", "mary fahl",
    "melissa etheridge", "margo price", "myrkur", "natalie merchant", "neko case", "nina simone",
    "norah jones", "pat benatar", "patti smith", "phoebe bridgers", "pj harvey",
    "rickie lee jones", "rumer", "sade", "samantha fish", "sarah blasko", "sarah jarosz",
    "sarah mclachlan", "sharon van etten", "sheryl crow", "sienna spiro", "sinead o'connor",
    "sinéad o'connor", "stevie nicks", "susanne sundfør", "susanne sundfor", "suzanne vega",
    "taylor swift", "tina turner", "tori amos", "tracy chapman", "weyes blood", "alissa white-gluz",
    "tarja", "tarja turunen", "floor jansen", "sharon den adel", "elize ryd",
    "alela diane & the hackles", "alison krauss and union station", "alison krauss & union station",
    "sharon van etten & the attachment theory", "eva cassidy"
}

KNOWN_PROG_ROCK = {
    "pink floyd", "yes", "genesis", "rush", "king crimson", "camel", "marillion",
    "porcupine tree", "steven wilson", "spock's beard", "neal morse", "the flower kings",
    "iq", "pendragon", "gentle giant", "kansas", "jethro tull", "transatlantic",
    "caravan", "focus", "renaissance", "big big train", "riverside", "gazpacho",
    "arena", "rpwl", "eloy", "airbag", "wobbler", "unitopia", "southern empire",
    "pattern-seeking animals", "mystery", "sylvan", "frost*", "karmakanic", "kaipa",
    "beardfish", "moon safari", "anekdoten", "anglagard", "änglagård", "pfm",
    "premiata forneria marconi", "banco del mutuo soccorso", "the pineapple thief",
    "threshold", "gong", "soft machine", "magma", "van der graaf generator",
    "peter hammill", "steve hackett", "fish", "rick wakeman", "the alan parsons project",
    "alan parsons", "asia", "uk", "curved air", "nektar", "tangerine dream",
    "hawkwind", "ozric tentacles", "public service broadcasting", "kavus torabi",
    "tim bowness", "no-man", "osi", "chroma key", "lonely robot", "john mitchell",
    "kino", "jelly fiche", "huis", "comedy of errors", "galahad", "pallas",
    "twelfth night", "subsignal", "the neal morse band", "flying colors", "lunatic soul",
    "believe", "anton roolaart", "3rd trip", "abstract", "abronia", "roine stolt",
    "coheed and cambria", "the mars volta", "polyphia", "plini", "animals as leaders",
    "intervals", "chon", "david gilmour", "roger waters", "jeff wayne", "kayak",
    "supersonic blues machine", "earthless", "maragold", "lee small"
}

KNOWN_HARD_ROCK_METAL = {
    "black sabbath", "iron maiden", "metallica", "megadeth", "slayer", "judas priest",
    "deep purple", "led zeppelin", "ac/dc", "ac dc", "guns n' roses", "guns n roses",
    "alice cooper", "aerosmith", "dio", "rainbow", "scorpions", "motörhead", "motorhead",
    "ozzy osbourne", "whitesnake", "def leppard", "van halen", "kiss", "accept", "saxon",
    "thin lizzy", "uriah heep", "blue öyster cult", "blue oyster cult", "ufo",
    "gary moore", "joe bonamassa", "stevie ray vaughan", "kenny wayne shepherd",
    "walter trout", "popa chubby", "rory gallagher", "ten years after", "gov't mule",
    "marcus king", "alcatrazz", "alcest", "alkaloid", "alterium", "amaranthe", "ambush",
    "angels of babylon", "angels in ashes", "angra", "angus mcsix", "armored saint",
    "as i lay dying", "athena xix", "aubrey", "avenged sevenfold", "axenstar", "beast",
    "black label society", "dream theater", "opeth", "symphony x", "queensrÿche",
    "queensryche", "fates warning", "mastodon", "gojira", "tool", "meshuggah",
    "in flames", "dark tranquillity", "arch enemy", "children of bodom", "nightwish",
    "epica", "within temptation", "blind guardian", "helloween", "gamma ray",
    "stratovarius", "sonata arctica", "kamelot", "avantasia", "sabaton", "powerwolf",
    "ghost", "five finger death punch", "disturbed", "slipknot", "system of a down",
    "korn", "rammstein", "volbeat", "halestorm", "the pretty reckless", "airbourne",
    "krokus", "quiet riot", "ratt", "dokken", "w.a.s.p.", "wasp", "twisted sister",
    "skid row", "mötley crüe", "motley crue", "poison", "cinderella", "great white",
    "tesla", "bad company", "free", "foghat", "grand funk railroad", "montrose",
    "ted nugent", "y&t", "rival sons", "greta van fleet", "dirty honey", "monster truck",
    "blackberry smoke", "clutch", "corrosion of conformity", "down", "kyuss",
    "monster magnet", "fu manchu", "sleep", "electric wizard", "candlemass",
    "saint vitus", "trouble", "pentagram", "cathedral", "paradise lost",
    "my dying bride", "amorphis", "katatonia", "moonspell", "rotting christ",
    "septicflesh", "dimmu borgir", "cradle of filth", "carcass", "morbid angel",
    "death", "cannibal corpse", "obituary", "deicide", "sepultura", "soulfly",
    "pantera", "damageplan", "lamb of god", "machine head", "trivium",
    "killswitch engage", "bullet for my valentine", "parkway drive", "architects",
    "bring me the horizon", "alice in chains", "soundgarden", "agriculture",
    "ancient vvisdom", "autumn's child", "bacchus", "bernard allison", "black country communion",
    "bon jovi", "buckcherry", "clint lowery", "creed", "daughtry", "dead daisies",
    "the dead daisies", "dominum", "drowning pool", "extreme", "firehouse", "firewind",
    "hardline", "heat", "h.e.a.t", "house of lords", "jackyl", "jorn", "king's x",
    "lynch mob", "michael schenker", "michael schenker group", "msg", "mr. big",
    "mr big", "myles kennedy", "night ranger", "pride & glory", "primal fear",
    "revolution saints", "richie kotzen", "savatage", "seether", "shinedown",
    "sixx:a.m.", "slash", "steel panther", "stryper", "the darkness", "the winery dogs",
    "thunder", "tremonti", "tyketto", "vandenberg", "warrant", "white lion",
    "winger", "yngwie malmsteen", "zakk wylde", "bruce dickinson", "halford",
    "fight", "blaze bayley", "circle ii circle", "doro", "warlock", "vixen",
    "castle rat", "haken", "clutch", "bad omens", "sleep token", "jinjer",
    "spiritbox", "in this moment", "the warning", "lord of the lost", "beast in black",
    "battle beast", "gloryhammer", "dynazty", "eclipse", "brother firetribe",
    "crazy lixx", "enuff z'nuff", "hardcore superstar", "crashdiet", "santa cruz",
    "shiraz lane", "airbourne", "bulletboys", "bad habit", "vanden plas"
}

def classify_genre(artist: str, album: str, folder_name: str, current_genre: str = "") -> str:
    a_lower = (artist or "").lower().strip()
    alb_lower = (album or "").lower().strip()
    fld_lower = (folder_name or "").lower().strip()
    g_lower = (current_genre or "").lower().strip()

    # 1. Christmas check
    full_text = f"{alb_lower} {fld_lower}"
    for pat in CHRISTMAS_PATTERNS:
        if re.search(pat, full_text):
            return "Christmas"

    # Explicit Overrides:
    # Santana kept in Rock
    if "santana" in a_lower:
        return "Rock"
    # Florence + the Machine in Rock
    if "florence" in a_lower and "machine" in a_lower:
        return "Rock"
    # Norah Jones & Eva Cassidy in Female
    if "norah jones" in a_lower or "eva cassidy" in a_lower:
        return "Female"

    # 2. Latina check
    if a_lower in KNOWN_LATINA_ARTISTS:
        return "Latina"
    for pat in LATINA_PATTERNS:
        if re.search(pat, g_lower) or re.search(pat, a_lower):
            return "Latina"

    # 3. Jazz check
    if a_lower in KNOWN_JAZZ_ARTISTS:
        return "Jazz"
    for pat in JAZZ_PATTERNS:
        if re.search(pat, g_lower):
            return "Jazz"

    # 4. Female check
    if a_lower in KNOWN_FEMALE_SOLO:
        return "Female"
    if ("female vocal" in g_lower or "female vocalist" in g_lower) and not any(re.search(p, g_lower) for p in HARD_ROCK_PATTERNS):
        return "Female"

    # 5. Progressive Rock check
    if a_lower in KNOWN_PROG_ROCK:
        return "Progressive Rock"
    for pat in PROG_PATTERNS:
        if re.search(pat, g_lower):
            return "Progressive Rock"

    # 6. Hard Rock check
    if a_lower in KNOWN_HARD_ROCK_METAL:
        return "Hard Rock"
    for pat in HARD_ROCK_PATTERNS:
        if re.search(pat, g_lower):
            return "Hard Rock"

    # 7. Default to Rock
    return "Rock"

# --- Cover Art Helpers ---

def detect_image_mime(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return "image/jpeg"

def parse_folder_name(folder_name: str):
    parts = [p.strip() for p in folder_name.split(" - ") if p.strip()]
    if len(parts) == 1:
        return parts[0], ""
    elif len(parts) == 2:
        return parts[0], parts[1]

    artist = parts[0]
    end_idx = len(parts)
    while end_idx > 1:
        last = parts[end_idx - 1]
        if re.match(r"^\d{4}$", last) or last.lower() in ["mp3", "flac", "hi-res", "[hi-res]"]:
            end_idx -= 1
        else:
            break

    album = " - ".join(parts[1:end_idx]) if end_idx > 1 else parts[1]
    return artist, album

def extract_band_and_album(file_path: str, folder_name: str):
    ext = os.path.splitext(file_path)[1].lower()
    artist, album, genre = "", "", ""

    if ext == ".flac":
        try:
            audio = FLAC(file_path)
            artist = audio.get("artist", [""])[0] or audio.get("albumartist", [""])[0]
            album = audio.get("album", [""])[0]
            genre = audio.get("genre", [""])[0]
        except Exception:
            pass
    elif ext == ".mp3":
        try:
            audio = MP3(file_path)
            if audio.tags:
                artist = str(audio.tags.get("TPE1", audio.tags.get("TPE2", "")))
                album = str(audio.tags.get("TALB", ""))
                genre = str(audio.tags.get("TCON", ""))
        except Exception:
            try:
                tags = ID3(file_path)
                artist = str(tags.get("TPE1", tags.get("TPE2", "")))
                album = str(tags.get("TALB", ""))
                genre = str(tags.get("TCON", ""))
            except Exception:
                pass
    elif ext == ".m4a":
        try:
            m4 = MP4(file_path)
            artist = m4.get("\xa9ART", [""])[0] or m4.get("aART", [""])[0]
            album = m4.get("\xa9alb", [""])[0]
            genre = m4.get("\xa9gen", [""])[0]
        except Exception:
            pass

    artist = artist.strip()
    album = album.strip()
    genre = genre.strip()

    folder_artist, folder_album = parse_folder_name(folder_name)
    if not artist:
        artist = folder_artist
    if not album:
        album = folder_album

    return artist, album, genre

def search_internet_cover(artist: str, album: str, verbose: bool = True):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    query = f"{artist} {album}".strip()

    # 1. iTunes Search API
    if verbose:
        print(f"    [Online Search] iTunes: '{query}'")
    url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=album&limit=10"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            results = data.get("results", [])
            best_art = None
            for r in results:
                cname = r.get("collectionName", "").lower()
                art = r.get("artworkUrl100")
                if art:
                    high_res = art.replace("100x100bb.jpg", "1000x1000bb.jpg")
                    if album.lower() in cname or cname in album.lower():
                        best_art = high_res
                        break
                    if not best_art:
                        best_art = high_res
            if best_art:
                if verbose:
                    print(f"    [Found] iTunes cover image")
                with urllib.request.urlopen(urllib.request.Request(best_art, headers=headers), timeout=15) as img_resp:
                    return img_resp.read()
    except Exception as e:
        if verbose:
            print(f"    [iTunes Warning] {e}")

    # 2. Deezer Search API
    if verbose:
        print(f"    [Online Search] Deezer: '{artist} - {album}'")
    deezer_url = f"https://api.deezer.com/search/album?q={urllib.parse.quote(query)}&limit=5"
    try:
        req = urllib.request.Request(deezer_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            for item in data.get("data", []):
                art = item.get("cover_xl") or item.get("cover_big")
                if art:
                    if verbose:
                        print(f"    [Found] Deezer cover image")
                    with urllib.request.urlopen(urllib.request.Request(art, headers=headers), timeout=15) as img_resp:
                        return img_resp.read()
    except Exception as e:
        if verbose:
            print(f"    [Deezer Warning] {e}")

    # 3. MusicBrainz / CoverArtArchive
    if verbose:
        print(f"    [Online Search] MusicBrainz: '{artist}' - '{album}'")
    mb_headers = {"User-Agent": "MusicCoverFetcher/1.0 (music@example.com)"}
    mb_query = f'artist:"{artist}" AND release:"{album}"'
    mb_url = f"https://musicbrainz.org/ws/2/release/?query={urllib.parse.quote(mb_query)}&fmt=json&limit=3"
    try:
        req = urllib.request.Request(mb_url, headers=mb_headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            for rel in data.get("releases", []):
                mbid = rel.get("id")
                caa_url = f"https://coverartarchive.org/release/{mbid}/front"
                try:
                    with urllib.request.urlopen(urllib.request.Request(caa_url, headers=mb_headers), timeout=10) as img_resp:
                        if img_resp.status == 200:
                            if verbose:
                                print(f"    [Found] CoverArtArchive cover image")
                            return img_resp.read()
                except Exception:
                    pass
    except Exception as e:
        if verbose:
            print(f"    [MusicBrainz Warning] {e}")

    return None

def file_has_cover_art(file_path: str) -> bool:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".flac":
        try:
            audio = FLAC(file_path)
            return len(audio.pictures) > 0
        except Exception:
            return False
    elif ext == ".mp3":
        try:
            audio = MP3(file_path)
            if audio.tags:
                for k in audio.tags.keys():
                    if k.startswith("APIC"):
                        return True
            return False
        except Exception:
            pass
        try:
            tags = ID3(file_path)
            for k in tags.keys():
                if k.startswith("APIC"):
                    return True
            return False
        except Exception:
            return False
    elif ext == ".m4a":
        try:
            m4 = MP4(file_path)
            return bool(m4.get("covr"))
        except Exception:
            return False
    return False

def embed_cover_art(file_path: str, image_data: bytes) -> bool:
    ext = os.path.splitext(file_path)[1].lower()
    mime = detect_image_mime(image_data)

    if ext == ".flac":
        try:
            audio = FLAC(file_path)
            audio.clear_pictures()
            pic = Picture()
            pic.type = 3
            pic.mime = mime
            pic.desc = "Front Cover"
            pic.data = image_data
            audio.add_picture(pic)
            audio.save()
            return True
        except Exception as e:
            print(f"    [Error] Embedding FLAC art {os.path.basename(file_path)}: {e}")
            return False

    elif ext == ".mp3":
        try:
            try:
                tags = ID3(file_path)
            except ID3NoHeaderError:
                tags = ID3()
            tags.delall("APIC")
            tags.add(
                APIC(
                    encoding=3,
                    mime=mime,
                    type=3,
                    desc="Front Cover",
                    data=image_data
                )
            )
            tags.save(file_path, v2_version=3)
            return True
        except Exception as e:
            print(f"    [Error] Embedding MP3 art {os.path.basename(file_path)}: {e}")
            return False

    elif ext == ".m4a":
        try:
            m4 = MP4(file_path)
            fmt = mutagen.mp4.MP4Cover.FORMAT_PNG if mime == "image/png" else mutagen.mp4.MP4Cover.FORMAT_JPEG
            m4["covr"] = [mutagen.mp4.MP4Cover(image_data, imageformat=fmt)]
            m4.save()
            return True
        except Exception as e:
            print(f"    [Error] Embedding M4A art {os.path.basename(file_path)}: {e}")
            return False

    return False

def set_file_genre(file_path: str, genre: str) -> bool:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".flac":
        try:
            audio = FLAC(file_path)
            audio["genre"] = [genre]
            audio.save()
            return True
        except Exception:
            return False

    elif ext == ".mp3":
        try:
            try:
                audio = MP3(file_path)
                if audio.tags is None:
                    audio.add_tags()
                audio.tags.delall("TCON")
                audio.tags.add(TCON(encoding=3, text=[genre]))
                audio.save(v2_version=3)
                return True
            except Exception:
                try:
                    tags = ID3(file_path)
                except ID3NoHeaderError:
                    tags = ID3()
                tags.delall("TCON")
                tags.add(TCON(encoding=3, text=[genre]))
                tags.save(file_path, v2_version=3)
                return True
        except Exception:
            return False

    elif ext == ".m4a":
        try:
            m4 = MP4(file_path)
            m4["\xa9gen"] = [genre]
            m4.save()
            return True
        except Exception:
            return False

    return False

def find_local_cover(folder_path: str):
    for name in ["cover.jpg", "Cover.jpg", "COVER.JPG", "cover.jpeg", "Cover.jpeg", "cover.png", "Cover.png"]:
        p = os.path.join(folder_path, name)
        if os.path.isfile(p) and os.path.getsize(p) > 0:
            return p
    return None

# --- Main Curation Engine ---

def process_music_library(target_path: str, genre_mode: str = None, fill_covers: bool = True, dry_run: bool = False):
    target_path = os.path.abspath(target_path)
    if os.name == "nt" and not target_path.startswith("\\\\?\\"):
        scan_root = "\\\\?\\" + target_path
    else:
        scan_root = target_path

    if not os.path.exists(scan_root):
        print(f"Error: Target path '{target_path}' does not exist.", file=sys.stderr)
        return False

    auto_genre = (genre_mode == "auto")
    fixed_genre = genre_mode if (genre_mode and genre_mode != "auto") else None

    print("=" * 65)
    print("MUSIC TAG & ALBUM ART CURATOR")
    print(f"Target Directory: {target_path}")
    print(f"Fill Covers:     {'Enabled' if fill_covers else 'Disabled'}")
    if auto_genre:
        print(f"Genre Mode:      AUTO-DETECT (7 Categories with User Rules)")
    elif fixed_genre:
        print(f"Genre Mode:      FIXED -> '{fixed_genre}'")
    else:
        print(f"Genre Mode:      UNCHANGED")
    print(f"Mode:            {'DRY-RUN (Preview Only)' if dry_run else 'ACTIVE (Modifying Tags)'}")
    print("=" * 65)

    # Walk directory tree
    folders_map = {}
    for root, dirs, files in os.walk(scan_root):
        audio_in_dir = [os.path.join(root, f) for f in files if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS]
        if audio_in_dir:
            folders_map[root] = audio_in_dir

    print(f"\nDiscovered {len(folders_map)} folders containing audio files.")

    stats = {
        "total_files": 0,
        "covers_already_present": 0,
        "covers_updated": 0,
        "covers_failed": 0,
        "genres_updated": Counter(),
    }

    for folder_path, audio_files in sorted(folders_map.items()):
        folder_display = folder_path.replace("\\\\?\\", "")
        folder_name = os.path.basename(folder_display)

        missing_covers = []
        for af in audio_files:
            stats["total_files"] += 1
            if fill_covers:
                if file_has_cover_art(af):
                    stats["covers_already_present"] += 1
                else:
                    missing_covers.append(af)

        need_logging = bool(missing_covers or genre_mode)
        if need_logging:
            print(f"\n[Folder] {folder_name} ({len(audio_files)} tracks)")

        # 1. Process Cover Art
        if fill_covers and missing_covers:
            print(f"  -> Missing cover art on {len(missing_covers)} files")
            cover_file = find_local_cover(folder_path)
            image_data = None

            # Step A: Local cover file
            if cover_file:
                print(f"  -> Found local cover file: {os.path.basename(cover_file)}")
                try:
                    with open(cover_file, "rb") as fp:
                        image_data = fp.read()
                except Exception as e:
                    print(f"  -> Error reading {cover_file}: {e}")

            # Step B: Sibling track reuse or online search
            if not image_data:
                for af in audio_files:
                    if af not in missing_covers:
                        ext = os.path.splitext(af)[1].lower()
                        try:
                            if ext == ".mp3":
                                mp = MP3(af)
                                for k, v in mp.tags.items():
                                    if k.startswith("APIC") and hasattr(v, "data") and v.data:
                                        image_data = v.data
                                        print(f"  -> Reusing art from sibling file: {os.path.basename(af)}")
                                        break
                            elif ext == ".flac":
                                fl = FLAC(af)
                                if fl.pictures:
                                    image_data = fl.pictures[0].data
                                    print(f"  -> Reusing art from sibling file: {os.path.basename(af)}")
                                    break
                        except Exception:
                            pass
                    if image_data:
                        break

                if not image_data:
                    sample_file = missing_covers[0]
                    artist, album, _ = extract_band_and_album(sample_file, folder_name)
                    print(f"  -> Searching internet for: Band='{artist}', Album='{album}'")
                    if not dry_run:
                        image_data = search_internet_cover(artist, album)

                if not image_data:
                    for f in os.listdir(folder_path):
                        if f.lower().endswith((".jpg", ".jpeg", ".png")):
                            p = os.path.join(folder_path, f)
                            if os.path.isfile(p) and os.path.getsize(p) > 0:
                                print(f"  -> Falling back to folder image: {f}")
                                with open(p, "rb") as fp:
                                    image_data = fp.read()
                                break

                # Save downloaded art as cover.jpg
                if image_data and not dry_run:
                    cov_out = os.path.join(folder_path, "cover.jpg")
                    if not os.path.exists(cov_out):
                        try:
                            with open(cov_out, "wb") as fp:
                                fp.write(image_data)
                            print(f"  -> Saved {os.path.basename(cov_out)}")
                        except Exception as e:
                            print(f"  -> Warning: Could not save cover.jpg: {e}")

            # Apply art to missing files
            if image_data:
                if dry_run:
                    print(f"  -> [DRY-RUN] Would embed cover art into {len(missing_covers)} files.")
                    stats["covers_updated"] += len(missing_covers)
                else:
                    for af in missing_covers:
                        if embed_cover_art(af, image_data):
                            stats["covers_updated"] += 1
                        else:
                            stats["covers_failed"] += 1
                    print(f"  -> Embedded cover art into {len(missing_covers)} files.")
            else:
                if not dry_run:
                    print(f"  -> [FAILED] Could not retrieve cover art.")
                    stats["covers_failed"] += len(missing_covers)

        # 2. Process Genre Tag
        if auto_genre or fixed_genre:
            for af in audio_files:
                if fixed_genre:
                    target_genre = fixed_genre
                else:
                    artist, album, cur_g = extract_band_and_album(af, folder_name)
                    target_genre = classify_genre(artist, album, folder_name, cur_g)

                if dry_run:
                    stats["genres_updated"][target_genre] += 1
                else:
                    if set_file_genre(af, target_genre):
                        stats["genres_updated"][target_genre] += 1
            if dry_run:
                print(f"  -> [DRY-RUN] Assigned genres: {dict(Counter(stats['genres_updated']))}")
            else:
                assigned_summary = ", ".join(f"{g}: {c}" for g, c in Counter(target_genre for af in audio_files).items())
                print(f"  -> Genre tags updated ({assigned_summary})")

    print("\n" + "=" * 65)
    print("CURATION SUMMARY")
    print(f"Total audio files scanned:         {stats['total_files']}")
    if fill_covers:
        print(f"Cover art already present:         {stats['covers_already_present']}")
        print(f"Cover art updated:                 {stats['covers_updated']}")
        print(f"Cover art failed:                  {stats['covers_failed']}")
    if genre_mode:
        print(f"\nGenre Tagging Breakdown ({sum(stats['genres_updated'].values())} files tagged):")
        for g, count in stats["genres_updated"].most_common():
            print(f"  • {g:18s}: {count:5d} tracks")
    print("=" * 65)
    return True

def main():
    parser = argparse.ArgumentParser(description="Automated Music Tag & Album Art Curator")
    parser.add_argument("path", help="Path to the music folder or root directory")
    parser.add_argument("--genre", "-g", help="Set genre tag (e.g. 'Hard Rock' or 'auto' for smart classification)")
    parser.add_argument("--auto-genre", "-a", action="store_true", help="Automatically detect and set genre using 7 curated categories")
    parser.add_argument("--no-covers", action="store_true", help="Do not process or download cover art")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Preview actions without modifying files")

    args = parser.parse_args()

    genre_mode = None
    if args.auto_genre or (args.genre and args.genre.lower() == "auto"):
        genre_mode = "auto"
    elif args.genre:
        genre_mode = args.genre

    process_music_library(
        target_path=args.path,
        genre_mode=genre_mode,
        fill_covers=not args.no_covers,
        dry_run=args.dry_run
    )

if __name__ == "__main__":
    main()
