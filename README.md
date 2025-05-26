# `karakeep-tts`

This repo contains a relatively simple script `main.py` which watches a bookmark list in [Karakeep](https://karakeep.app/) for new bookmarks, generates an MP3 using [ElevenLabs](https://elevenlabs.io/) from the text of the bookmark, and removes the bookmark from the list. A random voice is chosen for each article to try to keep things fresh. :)

It is intended for use with a project like [Audiobookshelf](https://www.audiobookshelf.org/) so that you can use Karakeep as a podcast feed for select articles.

## Usage
To use this script, there are a few required environment variables, described below. An example is provided in `example.env`, adjust appropriately and rename to `.env` for use.

To run the script, [install uv](https://docs.astral.sh/uv/getting-started/installation/) and run `uv run main.py`. Put it in a `tmux` or `screen` session if you prefer.

## Environment Variables

| Environment Variable     | Default Value           | Required | Description                                      |
|--------------------------|--------------------------|----------|--------------------------------------------------|
| `ELEVENLABS_API_KEY`     | None                     | Yes      | API key for ElevenLabs                           |
| `KARAKEEP_API_KEY`       | None                     | Yes      | API key for KaraKeep                             |
| `KARAKEEP_API_HOST`      | None                     | Yes      | API host URL for KaraKeep, e.g. `karakeep.example.com`                        |
| `MEDIA_PATH`             | `media`                  | No       | Path where media files are stored                |
| `BOOKMARK_LIST_NAME`     | `Podcast`                | No       | Name of the bookmark list                        |
| `ELEVENLABS_MODEL_ID`    | `eleven_turbo_v2_5`      | No       | ElevenLabs voice model ID                        |
| `SLEEP_INTERVAL`         | `60`                     | No       | Time (in seconds) to wait between intervals      |
| `HEALTHCHECK_URL`        | None                       | No       | URL for external healthcheck monitoring          |