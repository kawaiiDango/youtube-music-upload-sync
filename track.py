class Track:
  artist = None
  album = None
  title = None
  entityId = None
  filePath = None

  @staticmethod
  def fromDict(trackDict):
    track = Track()
    track.artist = trackDict["artist"]
    track.album = trackDict["album"]
    track.title = trackDict["title"]
    track.entityId = trackDict["entityId"]
    return track

  def toDict(self) -> dict:
    return {"artist": self.artist, "album": self.album, "title": self.title, "entityId": self.entityId}
  def __hash__(self):
    return hash(self.artist) ^ hash(self.album) ^ hash(self.title)
  def __eq__(self, other):
    return isinstance(other, Track) and self.artist == other.artist and self.album == other.album and self.title == other.title