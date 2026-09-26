import csv
from yt_dlp import YoutubeDL


def get_video_id(title, artist):

    searches = [
        f"{title} {artist} karaoke",
        f"{title} karaoke",
        f"{title} lyrics",
        f"{title}"
    ]

    for query in searches:

        try:

            with YoutubeDL({
                "quiet": True,
                "extract_flat": True
            }) as ydl:

                result = ydl.extract_info(
                    f"ytsearch1:{query}",
                    download=False
                )

            entries = result.get("entries", [])

            if entries:

                video_id = entries[0]["id"]

                print(
                    f"FOUND: {title} - {artist} -> {video_id}"
                )

                return video_id

        except Exception as error:

            print(
                f"ERROR: {title} - {artist}"
            )

            print(error)

    print(
        f"FAILED: {title} - {artist}"
    )

    return ""


with open(
    "database/songs_fixed.csv",
    "r",
    encoding="utf-8-sig",
    newline=""
) as file:

    songs = list(
        csv.DictReader(file)
    )


total_missing_before = sum(
    1
    for song in songs
    if not song["video_id"].strip()
)

print(
    f"\nMissing IDs before update: {total_missing_before}\n"
)


updated = 0

for song in songs:

    if song["video_id"].strip():
        continue

    print(
        f"\nSearching: {song['title']} - {song['artist']}"
    )

    video_id = get_video_id(
        song["title"],
        song["artist"]
    )

    if video_id:

        song["video_id"] = video_id

        updated += 1

        print(
            f"UPDATED ({updated})"
        )


with open(
    "database/songs_fixed.csv",
    "w",
    encoding="utf-8",
    newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=[
            "code",
            "title",
            "artist",
            "video_id",
            "source"
        ],
        quoting=csv.QUOTE_ALL
    )

    writer.writeheader()
    writer.writerows(songs)


total_missing_after = sum(
    1
    for song in songs
    if not song["video_id"].strip()
)

print("\n====================")
print(f"Updated: {updated}")
print(f"Still Missing: {total_missing_after}")
print("====================")


if total_missing_after:

    print("\nSONGS STILL MISSING IDs:\n")

    for song in songs:

        if not song["video_id"].strip():

            print(
                f'{song["code"]} | '
                f'{song["title"]} | '
                f'{song["artist"]}'
            )