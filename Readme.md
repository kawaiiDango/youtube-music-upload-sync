# Youtube Music Upload Sync

### Setup
- Put your music folders in `folders.json`
- `pip install --user -r requirements.txt`
-  Generate the browser.json file with: `ytmusicapi browser` and paste "Request Headers" from Firefox dev interface on:
-> Website : music.youtube.com
-> Firefox dev tools -> Network tab 
-> Status 200, Method POST, Domain music.youtube.com, File browse?..
-> Right click -> Copy Value -> Copy request headers

### Run
`python3 sync.py`

This script reads the tags from music files to compare against the uploads on youtube music, so make sure your music is tagged properly.

`--rebuild-cache` or `-rc` redownloads the list of uploaded songs from youtube music. You may encounter rate limits if you use this switch too frequently.

`--delete` or `-d` deletes uploaded songs which are not present on the disk from Youtube Music. Be careful with this switch as Youtube's tagging system can be different.