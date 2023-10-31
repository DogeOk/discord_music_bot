import random


class ServerInfo():
    songs = []
    now_playing = None

    def __init__(self, guild_id):
        self.guild_id = guild_id

    def shuffle_queue(self):
        temp = self.songs[:]
        self.songs = []
        while len(temp) > 0:
            ran = random.randint(0, len(temp) - 1)
            self.songs.append(temp[ran])
            del temp[ran]


class SongInfo():

    def __init__(self, link, link_type, song_name):
        self.link = link
        self.link_type = link_type
        self.song_name = song_name
