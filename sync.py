#!/usr/bin/env python3

import mutagen
import ytmusicapi
from ordered_set import OrderedSet

import json
import os
import sys

from track import Track
from getch import getch

SUPPORTED_EXTS = [".mp3", ".m4a", ".ogg", ".flac", ".wma"]
LOCAL_CACHE_JSON = "local_cache.json"
UPLOADED_CACHE_JSON = "library_cache.json"


def setup():
    global ytmusic
    # https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html#using-the-headers-in-your-project
    # generate the browser.json file with: 'ytmusicapi browser' and paste "Request Headers" from Firefox dev interface on :
    # Website : music.youtube.com
    # Firefox dev tools -> Network tab 
    # -> Status 200, Method POST, Domain music.youtube.com, File browse?..
    # -> Right click -> Copy Value -> Copy request headers
    ytmusic = ytmusicapi.YTMusic('browser.json')


def dumpToCache(tracks,filename):
    tracksList = []
    by_title = OrderedSet(sorted(tracks, key=lambda t: f"{t.artist}{t.title}"))  
    for track in by_title:
        tracksList.append(track.toDict())
    with open(filename, "w") as f:
        json.dump({"tracks": tracksList}, f, indent=4)

def loadCache(filename):
    tracksSet = OrderedSet()
    with open(filename, "r") as f:
        tracks = json.load(f)
        for trackDict in tracks["tracks"]:
            tracksSet.add(Track.fromDict(trackDict))
    return tracksSet


def getAllUploadedTracks(cleanCache=False):
    tracksSet = OrderedSet()
    if not os.path.exists(UPLOADED_CACHE_JSON) or cleanCache:
        print("Fetching list of uploaded songs. For a lot of songs, this may take a long time...")
        tracks = ytmusic.get_library_upload_songs(limit=100000)
        for yttrack in tracks:
            track = Track()
            if yttrack["artists"]:
                track.artist = yttrack["artists"][0]["name"].strip()
            if yttrack["album"]:
                track.album = yttrack["album"]["name"].strip()
            track.title = yttrack["title"].strip()
            track.entityId = yttrack["entityId"]
            tracksSet.add(track)
            dumpToCache(tracksSet,UPLOADED_CACHE_JSON)
        print("UploadedTracks cached to " + UPLOADED_CACHE_JSON)
    else:
        print("using " + UPLOADED_CACHE_JSON)
        tracksSet = loadCache(UPLOADED_CACHE_JSON)
    return tracksSet


def getAllLocalTracks(cleanCache=False):
    if not os.path.exists(LOCAL_CACHE_JSON) or cleanCache:
        print("Reading tags from local files...")
        folders = []
        tracks = OrderedSet()
        with open("folders.json", "r") as foldersJson:
            folders = json.loads(foldersJson.read())["folders"]
        for folder in folders:
            for root, subdirs, files in os.walk(folder):
                for filename in files:
                    filePath = os.path.join(root, filename)
                    _filename, fileExtension = os.path.splitext(filename)
                    fileExtension = fileExtension.lower()
                    if fileExtension in SUPPORTED_EXTS:
                        try:
                            metadata = mutagen.File(filePath)
                        except mutagen.MutagenError as e:
                            print(f"{filename}: {e}")
                            continue
                        if not metadata:
                            print("no tags for " + filePath)
                            continue
                        artist = None
                        album = None
                        title = None

                        if (fileExtension == ".flac" or fileExtension == ".ogg"):
                            if metadata.get("artist"):
                                artist = metadata.get("artist")[0]
                            elif metadata.get("albumartist"):
                                artist = metadata.get("albumartist")[0]
                            if metadata.get("album"):
                                album = metadata.get("album")[0]
                            if metadata.get("title"):
                                title = metadata.get("title")[0]
                        elif fileExtension == ".mp3":
                            if metadata.get("TPE1"):
                                artist = metadata.get("TPE1")[0]
                            elif metadata.get("TPE2"):
                                artist = metadata.get("TPE2")[0]
                            if metadata.get("TALB"):
                                album = metadata.get("TALB")[0]
                            if metadata.get("TIT2"):
                                title = metadata.get("TIT2")[0]
                        elif fileExtension == ".m4a":
                            if metadata.get("\xa9ART"):
                                artist = metadata.get("\xa9ART")[0]
                            elif metadata.get("aART"):
                                artist = metadata.get("aART")[0]
                            if metadata.get("\xa9alb"):
                                album = metadata.get("\xa9alb")[0]
                            if metadata.get("\xa9nam"):
                                title = metadata.get("\xa9nam")[0]
                        elif fileExtension == ".wma":
                            if metadata.get("Author"):
                                artist = metadata.get("Author")[0].value
                            elif metadata.get("WM/Composer"):
                                artist = metadata.get("WM/Composer")[0].value
                            if metadata.get("WM/AlbumTitle"):
                                album = metadata.get("WM/AlbumTitle")[0].value
                            if metadata.get("Title"):
                                title = metadata.get("Title")[0].value
                        if artist:
                            artist = artist.strip()
                            if ", " in artist:
                                splits = []
                                for split in artist.split(", "):
                                    splits.append(split.strip())
                                artist = ", ".join(splits)
                        if album:
                            album = album.strip()
                        if title:
                            title = title.strip()
                        if not title:
                            print("no tags for " + filePath)
                        else:
                            track = Track()
                            track.artist = artist
                            track.album = album
                            track.title = title
                            track.filePath = filePath
                            tracks.add(track)
        dumpToCache(tracks,LOCAL_CACHE_JSON)
        print("Local Tracks cached to " + LOCAL_CACHE_JSON)
    else:
        print("using local_cache.json")
        tracks = loadCache(LOCAL_CACHE_JSON)

    return tracks


def confirm(msg):
    print(msg + " [y/N]: ", end="", flush=True)
    ch = getch()
    print(ch)
    if ch == '\x03':
        raise KeyboardInterrupt
    return ch == 'y' or ch == 'Y'


def deleteTracks(tracks):
    deletedTracks = OrderedSet()
    confirmAll = False
    try:
        if sys.stdout.isatty():
            confirmAll = confirm("Confirm all (Y) or one by one (N)?")
        else:
            confirmAll = True
        for track in tracks:
            print("Delete " + str(track.artist) + " - " + str(track.title) +
                  " [" + str(track.album) + "]", end="")
            if confirmAll or confirm("?"):
                if confirmAll:
                    print()
                if track.entityId:
                    ytmusic.delete_upload_entity(track.entityId)
                    deletedTracks.add(track)
                else:
                    print("No entity id for this. You may want to rebuild cache (-rc)")
    except:
        pass
    return deletedTracks


def uploadTracks(tracks, uploadedTracks):
    print("Will upload " + str(len(tracks)) + " songs")
    i = 0
    for track in tracks:
        try:
            print("Uploading " + track.filePath + " " +
                  str(round(i * 100 / len(tracks), 2)) + "% " +
                  "(" + str(i + 1) + " / " + str(len(tracks)) + ")")
            res = ytmusic.upload_song(track.filePath)
            if res != 'STATUS_SUCCEEDED':
                if res.status_code == 401:
                    print("unauthorized")
                    break
                elif res.status_code != 409:
                    # may fail with 409 (duplicate), which is a success
                    print("failed", res)
                    continue
            uploadedTracks.add(track)
            # print(track.toDict())
            i += 1
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("Exception: ", str(e))
        except:
            print("Unexpected error:", sys.exc_info()[0])

    return uploadedTracks


if __name__ == "__main__":
    setup()
    try:
        # List tracks (from cache or fetch)
        cleanCache =  ("--rebuild-cache" in sys.argv or "-rc" in sys.argv)
        uploadedTracks = getAllUploadedTracks(cleanCache=cleanCache)
        localTracks = getAllLocalTracks(cleanCache=cleanCache)
        print("=> Local tracks: " + str(len(localTracks)))
        print("=> Uploaded tracks: " + str(len(uploadedTracks)))

        # Delete tracks if required
        tracksToDelete = uploadedTracks - localTracks
        if ("--delete" in sys.argv or "-d" in sys.argv) and len(tracksToDelete) > 0:
            print("==> To delete: " + str(len(tracksToDelete)) + " songs")
            input("Press Enter to start deleting...")
            deletedTracks = deleteTracks(tracksToDelete)
            dumpToCache(uploadedTracks-deletedTracks, UPLOADED_CACHE_JSON)
    
        # Upload tracks       
        tracksToUpload = localTracks - uploadedTracks
        print("==> To upload: " + str(len(tracksToUpload)))
        if len(tracksToUpload) > 0:
            input("Press Enter to start uploading...")
            uploadedTracks = uploadTracks(tracksToUpload, uploadedTracks)
            dumpToCache(uploadedTracks, UPLOADED_CACHE_JSON)
    except:
        print("Unexpected error:", sys.exc_info()[0])
        raise