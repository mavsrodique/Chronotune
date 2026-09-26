from __future__ import annotations

import csv
import re
from pathlib import Path
from threading import Lock
from typing import Any
from yt_dlp import YoutubeDL
from flask import Flask, jsonify, render_template, request
from ytmusicapi import YTMusic

yt = YTMusic()

app = Flask(__name__)

BASE_DIRECTORY = Path(__file__).resolve().parent
SONGS_FILE = BASE_DIRECTORY / "database" / "songs_fixed.csv"

song_queue: list[dict[str, Any]] = []
queue_lock = Lock()
next_queue_id = 1


def load_songs() -> list[dict[str, str]]:

    if not SONGS_FILE.exists():
        return []

    with SONGS_FILE.open("r", newline="", encoding="utf-8-sig") as file:

        rows = csv.DictReader(file)

        return [
            {
                "code": (row.get("code") or "").strip(),
                "title": (row.get("title") or "").strip(),
                "artist": (row.get("artist") or "").strip(),
                "video_id": (row.get("video_id") or "").strip(),
                "source": (row.get("source") or "").strip(),
            }
            for row in rows
        ]


def normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def search_songs(query: str) -> list[dict[str, str]]:

    query = normalize_text(query)

    if not query:
        return []

    results = []

    for song in load_songs():

        if (
            query in normalize_text(song["code"])
            or query in normalize_text(song["title"])
            or query in normalize_text(song["artist"])
        ):
            results.append(song)

    return results


def save_song_to_csv(song):
    songs = load_songs()

    new_title = normalize_text(song["title"])
    new_artist = normalize_text(song["artist"])

    # Check if this exact title + artist already exists
    for existing in songs:

        existing_title = normalize_text(existing["title"])
        existing_artist = normalize_text(existing["artist"])

        if existing_title == new_title and existing_artist == new_artist:
            # Update the existing video's ID
            existing["video_id"] = song["video_id"]

            with SONGS_FILE.open(
                "w",
                newline="",
                encoding="utf-8",
            ) as file:

                writer = csv.writer(
                    file,
                    quoting=csv.QUOTE_ALL,
                )

                writer.writerow(
                    [
                        "code",
                        "title",
                        "artist",
                        "video_id",
                        "source",
                    ]
                )

                for saved in songs:
                    writer.writerow(
                        [
                            saved["code"],
                            saved["title"],
                            saved["artist"],
                            saved["video_id"],
                            saved["source"],
                        ]
                    )

            print(
                "CSV UPDATED:",
                song["title"],
                "-",
                song["artist"],
                "→",
                song["video_id"],
            )

            return

    # No existing song → add it
    with SONGS_FILE.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(
            file,
            quoting=csv.QUOTE_ALL,
        )

        writer.writerow(
            [
                song["code"],
                song["title"],
                song["artist"],
                song["video_id"],
                song["source"],
            ]
        )

    print(
        "CSV ADDED:",
        song["title"],
        "-",
        song["artist"],
        "→",
        song["video_id"],
    )


def update_video_id(title: str, artist: str, new_video_id: str):

    songs = load_songs()

    with SONGS_FILE.open("w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file, quoting=csv.QUOTE_ALL)

        writer.writerow(["code", "title", "artist", "video_id", "source"])

        for song in songs:

            if normalize_text(song["title"]) == normalize_text(
                title
            ) and normalize_text(song["artist"]) == normalize_text(artist):
                song["video_id"] = new_video_id

            writer.writerow(
                [
                    song["code"],
                    song["title"],
                    song["artist"],
                    song["video_id"],
                    song["source"],
                ]
            )


# def parse_song_title(video_title: str):

#     title = video_title

#     remove_words = [
#         "(karaoke version)",
#         "(karaoke)",
#         "[karaoke]",
#         "karaoke version",
#         "karaoke",
#         "lyrics",
#         "official karaoke",
#         "| karaoke"
#     ]

#     for word in remove_words:
#         title = re.sub(
#             re.escape(word),
#             "",
#             title,
#             flags=re.IGNORECASE
#         )

#     title = title.strip()

#     if " - " in title:

#         artist, song = title.split(" - ", 1)

#         return (
#             song.strip(),
#             artist.strip()
#         )


#     return (
#         title.strip(),
#         "Unknown Artist"
#     )
def choose_best_karaoke_video(entries, title, artist):
    import re

    def normalize(text):
        text = (text or "").lower()

        # Remove brackets/parentheses content
        text = re.sub(r"\([^)]*\)", " ", text)
        text = re.sub(r"\[[^\]]*\]", " ", text)

        # Remove punctuation
        text = re.sub(r"[^a-z0-9\s]", " ", text)

        # Normalize spaces
        text = re.sub(r"\s+", " ", text).strip()

        return text

    wanted_title = normalize(title)
    wanted_artist = normalize(artist)

    # Things that are NOT karaoke
    forbidden = [
        "tutorial",
        "lesson",
        "how to play",
        "how to sing",
        "guitar",
        "piano tutorial",
        "guitar tutorial",
        "bass tutorial",
        "drum tutorial",
        "reaction",
        "reacts",
        "cover",
        "live performance",
        "concert",
        "performance",
        "acoustic cover",
        "dance tutorial",
        "vocal lesson",
        "singing lesson",
        "karaoke tutorial",
    ]

    # Things that strongly indicate karaoke
    preferred = [
        "karaoke",
        "instrumental",
        "minus one",    
        "karaoke version",
    ]

    candidates = []

    for video in entries:
        video_id = video.get("id", "")
        video_title = video.get("title", "")

        if not video_id or not video_title:
            continue

        normalized = normalize(video_title)
        raw = video_title.lower()

        # Reject obvious garbage first
        if any(term in raw for term in forbidden):
            continue

        score = 0

        # TITLE MATCH
        if wanted_title == normalized:
            score += 200

        elif wanted_title in normalized:
            score += 120

        else:
            # Require at least some title similarity
            title_words = wanted_title.split()

            matched_words = sum(1 for word in title_words if word in normalized)

            if title_words:
                similarity = matched_words / len(title_words)

                if similarity >= 0.8:
                    score += 80
                elif similarity >= 0.5:
                    score += 30
                else:
                    continue

        # ARTIST MATCH
        if wanted_artist:
            if wanted_artist in normalized:
                score += 150
            else:
                # Artist mismatch is heavily penalized
                score -= 100

        # KARAOKE INDICATORS
        for term in preferred:
            if term in raw:
                score += 25

        # Strong bonus for exact karaoke wording
        if "karaoke" in raw:
            score += 60

        # Slight preference for guide vocals
        if "with guide" in raw or "guide vocals" in raw:
            score += 20

        candidates.append((score, video))

    if not candidates:
        return None

    # Highest score wins
    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    best_score, best_video = candidates[0]

    print("=" * 50)
    print("KARAOKE SELECTION")
    print("REQUESTED:", title, "-", artist)
    print("CANDIDATES:", len(candidates))

    for score, video in candidates[:10]:
        print(
            score,
            "|",
            video.get("title"),
            "|",
            video.get("id"),
        )

    print("SELECTED:", best_video.get("title"))
    print("SELECTED ID:", best_video.get("id"))
    print("=" * 50)

    return best_video


def search_youtube_and_save(query: str):
    import re

    def normalize(text):
        text = (text or "").lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    # ---------------------------------
    # SEARCH YOUTUBE MUSIC
    # ---------------------------------

    music_results = yt.search(
        query,
        filter="songs",
    )

    if not music_results:
        return None

    query_normalized = normalize(query)

    # Find the best YouTube Music result
    best_music = None
    best_score = -1

    for music in music_results:
        music_title = music.get("title", "")

        artists = music.get("artists", [])

        artist_names = [artist.get("name", "") for artist in artists]

        combined = normalize(music_title + " " + " ".join(artist_names))

        score = 0

        # Every query word that appears in the result
        for word in query_normalized.split():
            if word in combined:
                score += 1

        # STRONG artist match
        for artist_name in artist_names:
            artist_normalized = normalize(artist_name)

            if artist_normalized in query_normalized:
                score += 100

        print(
            "YT MUSIC CANDIDATE:",
            music_title,
            artist_names,
            "SCORE:",
            score,
        )

        if score > best_score:
            best_score = score
            best_music = music

    if not best_music:
        return None

    # ---------------------------------
    # CLEAN METADATA
    # ---------------------------------

    clean_title = best_music.get(
        "title",
        query,
    )

    artists = best_music.get(
        "artists",
        [],
    )

    clean_artist = artists[0]["name"] if artists else "Unknown Artist"

    print("=" * 50)
    print("FINAL YT MUSIC RESULT")
    print("QUERY:", query)
    print("TITLE:", clean_title)
    print("ARTIST:", clean_artist)
    print("SCORE:", best_score)
    print("=" * 50)

    # ---------------------------------
    # SEARCH KARAOKE
    # ---------------------------------

    with YoutubeDL(
        {
            "quiet": True,
            "extract_flat": True,
        }
    ) as ydl:

        result = ydl.extract_info(
            f"ytsearch20:{clean_title} {clean_artist} karaoke",
            download=False,
        )

    entries = result.get(
        "entries",
        [],
    )

    if not entries:
        return None

    video = choose_best_karaoke_video(
        entries,
        clean_title,
        clean_artist,
    )

    if not video:
        return None

    # ---------------------------------
    # CREATE SONG
    # ---------------------------------

    song = {
        "code": "",
        "title": clean_title,
        "artist": clean_artist,
        "video_id": video.get("id", "").strip(),
        "source": "open",
    }

    print("FINAL SONG:", song)

    save_song_to_csv(song)

    return song


def add_to_queue(song: dict[str, str]):

    global next_queue_id

    with queue_lock:

        queued_song = {**song, "queue_id": next_queue_id}

        song_queue.append(queued_song)
        next_queue_id += 1

    return queued_song


@app.route("/")
def home():

    return render_template("index.html")


@app.get("/api/search")
def api_search():

    query = request.args.get("q", "")

    print("SEARCH:", query)

    results = search_songs(query)

    print("CSV RESULTS:", len(results))

    if not results:

        print("Searching YouTube...")

        youtube_song = search_youtube_and_save(query)

        print("YT RESULT:", youtube_song)

        if youtube_song:
            results = [youtube_song]

    return jsonify({"query": query, "count": len(results), "results": results})


# @app.get("/api/fix-video")
# def fix_video():

#     query = request.args.get("q", "").strip()
#     title = request.args.get("title", "").strip()
#     artist = request.args.get("artist", "").strip()
#     current_video_id = request.args.get("current_video_id", "").strip()

#     if not query:
#         return jsonify({"error": "Missing query"}), 400

#     try:

#         with YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:

#             result = ydl.extract_info(
#                 f"ytsearch20:{title} {artist} karaoke", download=False
#             )

#         entries = result.get("entries", [])

#         if not entries:
#             return jsonify({"error": "No replacement found"}), 404

#         filtered_entries = [
#             video for video in entries if video.get("id") != current_video_id
#         ]

#         video = choose_best_karaoke_video(filtered_entries, title, artist)

#         if not video:
#             return jsonify({"error": "No suitable karaoke video found"}), 404

#         new_video_id = video["id"]

#         if title and artist:
#             update_video_id(title, artist, new_video_id)

#         return jsonify({"video_id": new_video_id})

#     except Exception as error:

#         print("FIX VIDEO ERROR:", error)

#         return jsonify({"error": str(error)}), 500


@app.get("/api/queue")
def api_queue():

    with queue_lock:
        return jsonify({"queue": song_queue})


@app.post("/api/queue")
def reserve_song():

    payload = request.get_json(silent=True) or {}

    # OPEN SONG
    if payload.get("source") == "open":

        song = {
            "code": "",
            "title": payload.get("title", "").strip(),
            "artist": payload.get("artist", "").strip(),
            "video_id": payload.get("video_id", "").strip(),
            "source": "open",
        }

        return jsonify({"message": "Song reserved.", "song": add_to_queue(song)}), 201

    # PLATINUM SONG
    code = str(payload.get("code", "")).strip()

    song = next((item for item in load_songs() if item["code"] == code), None)

    if song is None:
        return jsonify({"error": "Song not found."}), 404

    with queue_lock:

        if any(item["code"] == code for item in song_queue):
            return jsonify({"error": "Song already in queue."}), 400

    return jsonify({"message": "Song reserved.", "song": add_to_queue(song)}), 201


@app.delete("/api/queue/<int:queue_id>")
def remove_from_queue(queue_id):

    with queue_lock:

        for index, song in enumerate(song_queue):

            if song["queue_id"] == queue_id:

                removed = song_queue.pop(index)

                return jsonify({"message": "Song removed.", "song": removed})

    return jsonify({"error": "Song not found."}), 404


@app.post("/api/fix-video")
def fix_video_advanced():
    payload = request.get_json(silent=True) or {}

    title = payload.get("title", "").strip()
    artist = payload.get("artist", "").strip()
    rejected_videos = payload.get("rejected_videos", [])

    if not title:
        return jsonify({"error": "Missing title"}), 400

    try:
        with YoutubeDL(
            {
                "quiet": True,
                "extract_flat": True,
            }
        ) as ydl:

            result = ydl.extract_info(
                f"ytsearch200:{title} {artist} karaoke with guide",
                download=False,
            )

        entries = result.get("entries", [])

        if not entries:
            return jsonify({"error": "No search results found"}), 404

        filtered_entries = []

        for video in entries:
            video_id = video.get("id", "")

            if not video_id:
                continue

            if video_id in rejected_videos:
                continue

            filtered_entries.append(video)

        if not filtered_entries:
            return jsonify({"error": "No more karaoke videos available"}), 404

        video = choose_best_karaoke_video(
            filtered_entries,
            title,
            artist,
        )

        if not video:
            return jsonify({"error": "No suitable karaoke video found"}), 404

        new_video_id = video.get("id", "")
        
        update_video_id(
            title,
            artist,
            new_video_id,
        )

        if not new_video_id:
            return jsonify({"error": "Selected video has no video ID"}), 404

        print("=" * 50)
        print("FIX CURRENT VIDEO")
        print("TITLE:", title)
        print("ARTIST:", artist)
        print("REJECTED:", rejected_videos)
        print("SELECTED:", new_video_id)
        print("=" * 50)

        return jsonify(
            {
                "video_id": new_video_id,
            }
        )

    except Exception as error:

        print("FIX VIDEO ERROR:", error)

        return (
            jsonify(
                {
                    "error": str(error),
                }
            ),
            500,
        )


@app.post("/api/reset-queue")
def reset_queue():

    global song_queue
    global next_queue_id

    with queue_lock:

        song_queue.clear()
        next_queue_id = 1

    return jsonify({"message": "Queue reset."})


@app.get("/api/all-songs")
def api_all_songs():

    songs = load_songs()

    return jsonify({"count": len(songs), "songs": songs[:50]})


print("🎤 Karaoke System Starting...")
print("Loading song database...")

# your CSV/song loading code here

print("Loading settings...")

# other startup code

print("Starting web server...")

if __name__ == "__main__":

    app.run(debug=True)
