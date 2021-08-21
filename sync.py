#!/usr/bin/env python3

import mutagen
from ytmusicapi import YTMusic
from ordered_set import OrderedSet

import json
import os
import sys

from track import Track
from getch import getch

SUPPORTED_EXTS = [".mp3", ".m4a", ".ogg", ".flac", ".wma"]


def setup():
    global ytmusic
    if os.path.exists("headers_auth_raw.txt"):
        with open("headers_auth_raw.txt", "r") as headersRaw:
            YTMusic.setup(filepath="headers_auth.json",
                          headers_raw=headersRaw.read())
        os.remove("headers_auth_raw.txt")
    ytmusic = YTMusic('headers_auth.json')


def dumpToCache(tracks):
    tracksList = []
    for track in tracks:
        tracksList.append(track.toDict())
    with open("library_cache.json", "w") as f:
        json.dump({"tracks": tracksList}, f, indent=4)


def loadCache():
    tracksSet = OrderedSet()
    with open("library_cache.json", "r") as f:
        tracks = json.load(f)
        for trackDict in tracks["tracks"]:
            tracksSet.add(Track.fromDict(trackDict))
    return tracksSet


def getAllUploadedTracks():
    tracksSet = OrderedSet()
    if not os.path.exists("library_cache.json") or \
            ("--rebuild-cache" in sys.argv or "-rc" in sys.argv):
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
            dumpToCache(tracksSet)
    else:
        print("using library_cache.json")
        tracksSet = loadCache()
    return tracksSet


def getAllLocalTracks():
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
    if not ("--delete" in sys.argv or "-d" in sys.argv) or len(tracks) == 0:
        return deletedTracks
    print("Will delete " + str(len(tracks)) + " songs from Youtube Music")
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
    uploadedTracks = getAllUploadedTracks()
    localTracks = getAllLocalTracks()

    deletedTracks = deleteTracks(uploadedTracks - localTracks)
    if len(deletedTracks) > 0:
        uploadedTracks = uploadedTracks - deletedTracks
        dumpToCache(uploadedTracks)

    tracksToUpload = localTracks - uploadedTracks
    if len(tracksToUpload) > 0:
        uploadedTracks = uploadTracks(tracksToUpload, uploadedTracks)
        dumpToCache(uploadedTracks)
