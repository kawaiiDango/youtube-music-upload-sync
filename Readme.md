# Youtube Music Upload Sync

### Setup
Put your music folders in `folders.json`
Copy the request headers into `headers_auth_raw.txt`
(See https://ytmusicapi.readthedocs.io/en/latest/setup.html#authenticated-requests)
`pip install --user -r requirements.txt`

### Run
`python3 sync.py`

This script reads the tags from music files to compare against the uploads on youtube music, so make sure your music is tagged properly.

`--rebuild-cache` or `-rc` redownloads the list of uploaded songs from youtube music. You may encounter rate limits if you use this switch too frequently.

`--delete` or `-d` deletes uploaded songs which are not present on the disk from Youtube Music. Be careful with this switch as Youtube's tagging system can be different.