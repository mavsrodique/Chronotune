import csv

with open(
    "database/songs_fixed.csv",
    "r",
    encoding="utf-8-sig"
) as file:

    songs = list(csv.DictReader(file))

missing = []

for song in songs:

    if not song["video_id"].strip():

        missing.append(song)

print(f"\nMissing video IDs: {len(missing)}\n")

for song in missing:

    print(
        f'{song["code"]} | '
        f'{song["title"]} | '
        f'{song["artist"]}'
    )

with open(
    "database/songs_fixed.csv",
    "w",
    newline="",
    encoding="utf-8"
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

print("\nCSV rewritten with quotes.")