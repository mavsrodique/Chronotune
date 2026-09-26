# Karaoke App - Project Context
Project Goal
Build a personal-use karaoke system that runs locally as a web application.
The app should imitate the experience of a real karaoke machine (like Platinum Karaoke):

Search songs
Browse results
Reserve songs
Maintain a queue
Play karaoke videos
The app will run on the user's laptop through a localhost server and open in Brave browser.

# Technology Stack
Backend
Python + Flask

Frontend
HTML CSS JavaScript

Database
Start:

CSV files
Later:

SQLite database
Browser
Brave Browser will be used as the interface.

# Main System Flow
User:

Searches: "Zombie"

System:

Search local song database.

If found:

Show song code
Show title
Show artist
Use saved video ID
If not found:

Search for a karaoke version online.
Prefer karaoke/instrumental versions.
Song Database Structure
Every song should contain:

code
title
artist
video_id
source

Example:

{ code: "3416", title: "I WANT YOU BACK", artist: "NSYNC", video_id: "", source: "database" }

# Search System
Search should support:

Song code
Song title
Artist name

Example:

Search:

3416

returns:

3416 I WANT YOU BACK NSYNC

Search:

NSYNC

returns:

I WANT YOU BACK - NSYNC

# Online Search Logic
If a song is not found locally:

Modify the search query internally:

User input:

Zombie

System search:

Zombie karaoke

Prioritize results containing:

karaoke
instrumental
minus one
no vocals
Avoid prioritizing:

official music video
live
reaction videos
Queue System
Queue stores:

song code
title
artist
video ID
Example:

# QUEUE

3416 - I WANT YOU BACK - NSYNC
5000 - Zombie - The Cranberries
UI Design
The interface should resemble a karaoke machine.

# Requirements
Large buttons
Easy operation
Dark theme preferred
Simple layout
Touchscreen friendly

Main sections:
SEARCH

RESULT

RESERVE BUTTON

QUEUE

NOW PLAYING

# Development Plan
# Phase 1
Create Flask application.

Features:
localhost server
basic UI
search box
song display
queue

# Phase 2
Create song database.

Features:
import song lists
search by code/title/artist

# Phase 3
Add online song discovery.

Features:
find new songs
save new video IDs

# Phase 4
Add playback system.

