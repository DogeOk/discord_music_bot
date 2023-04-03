import random


class ServerInfo():
    song_type = []
    queue = []
    song_names = []
    now_playing = ''
    queue_message_id = []
    player_message_id = 0
    queue_list_page_number = 0

    def shuffle_queue(self):
        temp = self.queue[:]
        temp2 = self.song_names[:]
        self.queue = []
        self.song_names = []
        while len(temp) > 0:
            ran = random.randint(0, len(temp) - 1)
            self.queue.append(temp[ran])
            self.song_names.append(temp2[ran])
            del temp[ran]
            del temp2[ran]
