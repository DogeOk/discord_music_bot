import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
from os import listdir
from os.path import isfile, join
import random
import os
from threading import Thread
from settings import settings
import subprocess


queues = {}
now_playing = {}

def check_queue(ctx):
    guild_id = ctx.message.guild.id
    voice = ctx.guild.voice_client
    if (guild_id in queues):
        if (len(queues[guild_id]["playlist"]) != 0):
            voice.play(FFmpegPCMAudio("./music/" + queues[guild_id]["playlist"][0]), after = lambda x = None: check_queue(ctx) )
            now_playing[guild_id] = queues[guild_id]["song_name"][0]
            del queues[guild_id]["playlist"][0]
            del queues[guild_id]["song_name"][0]
        else:
            del queues[guild_id]


def shuffle_queue(ctx):
    guild_id = ctx.message.guild.id
    temp = queues[guild_id]["playlist"][:]
    temp2 =  queues[guild_id]["song_name"][:]
    queues[guild_id]["playlist"] = []
    queues[guild_id]["song_name"] = []
    while len(temp) > 0:
        ran = random.randint(0, len(temp) - 1)
        queues[guild_id]["playlist"].append(temp[ran])
        queues[guild_id]["song_name"].append(temp2[ran])
        del temp[ran]
        del temp2[ran]


def check_play(ctx, del_path):
    if (del_path != None):
        os.remove(del_path)
    guild_id = ctx.message.guild.id
    voice = ctx.guild.voice_client
    if (guild_id in queues):
        if (len(queues[guild_id]["playlist"]) != 0):
            link = queues[guild_id]["playlist"][0][0]
            playlist_counter = queues[guild_id]["playlist"][0][1]
            os.system(f"yt-dlp -f bestaudio --playlist-items \"{playlist_counter}\" -o \"./yt/{guild_id}/%(title)s.%(ext)s\" \"{link}\"")
            path = f"./yt/{guild_id}/" + listdir(f"./yt/{guild_id}")[0]
            voice.play(FFmpegPCMAudio(path), after = lambda x = None: check_play(ctx, path))
            del queues[guild_id]["playlist"][0]
            now_playing[guild_id] = queues[guild_id]["song_name"][0]
            del queues[guild_id]["song_name"][0]
        else:
            del queues[guild_id]
            os.rmdir(f"./yt/{guild_id}/")


def check_link(guild_id, link, is_playlist):
    if (is_playlist == None):
        is_playlist = check_playlist(link)
    if (not is_playlist):
        song_name = subprocess.check_output(f"yt-dlp --no-warnings --ignore-errors --simulate --get-title {link}", shell=True).decode("windows_1251")[:-1]
        queues[guild_id]["playlist"].append([link, 1])
        queues[guild_id]["song_name"].append(song_name)
    else:
        song_names = subprocess.check_output(f"yt-dlp --no-warnings --ignore-errors --simulate --get-title {link}", shell=True).decode("windows_1251").split("\n")[:-1]
        i = 1
        for song_name in song_names:
            queues[guild_id]["playlist"].append([link, i])
            queues[guild_id]["song_name"].append(song_name)
            i += 1


def check_playlist(link):
    return len(subprocess.check_output(f"yt-dlp --playlist-items \"1, 2\" --simulate --get-id {link}", shell=True).decode("windows_1251").split("\n")[:-1]) > 1


bot = commands.Bot(command_prefix = settings['prefix'], help_command = None)

@bot.event
async def on_ready():
    await bot.change_presence(activity = discord.Game(name = f"{settings['prefix']}help"))


@bot.command()
async def help(ctx):
    author = ctx.message.author
    await ctx.send(f"""Привет, {author.mention}. Вот список доступных команд:
{settings['prefix']}play(p) - добавление в очередь песни по ссылке.
{settings['prefix']}radio(r) - запускает радио.
{settings['prefix']}leave(l) - выкидывает бота из голосового канала
{settings['prefix']}skip(s) n - пропустить трек (вместо n указать кол-во пропускаемых песен)
{settings['prefix']}queue(q) n - список треков (вместо n указать номер страницы)
В скобках содержатся сокращённые вариации команд.
""")


for cmd in ("play", "p"):
    @bot.command(name = cmd)
    async def play(ctx):
        message = ctx.message.content.split(' ')
        guild_id = ctx.message.guild.id
        voice = ctx.guild.voice_client
        if (len(message) < 2):
            return
        if (voice == None):
            await ctx.message.author.voice.channel.connect()
        link = message[1]
        if (guild_id in queues):
            if (queues[guild_id]["play_mode"] == "radio"):
                return
            check_link_thread = Thread(target = check_link, args = (guild_id, link, None))
            check_link_thread.start()
        else:
            queues[guild_id] = {}
            queues[guild_id]["playlist"] = []
            queues[guild_id]["song_name"] = []
            queues[guild_id]["play_mode"] = "yt"
            check_link(guild_id, link, None)
            yt_play_thread = Thread(target = check_play, args = (ctx, None))
            yt_play_thread.start()


for cmd in ("radio", "r"):
    @bot.command(name = cmd)
    async def radio(ctx):
        guild_id = ctx.message.guild.id
        voice = ctx.guild.voice_client
        if (guild_id in queues):
            if (queues[guild_id]["play_mode"] == "yt"):
                await ctx.send("Запуск радио режима невозможен, пока прослушиваются песни по запросам.")
        if (voice == None):
            await ctx.message.author.voice.channel.connect()
        queues[guild_id] = {}
        queues[guild_id]["playlist"] = [f for f in listdir("./music") if isfile(join("./music", f))]
        queues[guild_id]["song_name"] = queues[guild_id]["playlist"][:]
        queues[guild_id]["play_mode"] = "radio";
        await ctx.send(f"Запускаю радио.")
        shuffle_queue(ctx)
        check_queue(ctx)


for cmd in ("skip", "s"):
    @bot.command(name = cmd)
    async def skip(ctx):
        voice = ctx.guild.voice_client
        guild_id = ctx.message.guild.id
        message = ctx.message.content.split(' ')
        if (len(message) >= 2):
            n = int(message[1])
        else:
            n = 1
        del queues[guild_id]["playlist"][:n-1]
        del queues[guild_id]["song_name"][:n-1]
        voice.stop()


for cmd in ("queue", "q"):
    @bot.command(name = cmd)
    async def queue(ctx):
        guild_id = ctx.message.guild.id
        message = ctx.message.content.split(' ')
        if (len(message) >= 2):
            n = int(message[1])
        else:
            n = 1
        range_param = 10 * n
        if n == len(queues[guild_id]["song_name"]) // 10 + 1:
            range_param = len(queues[guild_id]["song_name"])
        text = f"Сейчас играет: {now_playing[guild_id]}\nСледующие треки:\n"
        for i in range(10 * (n - 1), range_param):
            text += f"{i + 1}. {queues[guild_id]['song_name'][i]} \n"
        text += f"Страница {n} из {len(queues[guild_id]['song_name']) // 10 + 1}"
        await ctx.send(text)


for cmd in ("leave", "l"):
    @bot.command(name = cmd)
    async def leave(ctx):
        guild_id = ctx.message.guild.id
        if (guild_id in queues):
            del queues[guild_id]
            voice = ctx.guild.voice_client
            voice.stop()
        await ctx.guild.voice_client.disconnect()


for cmd in ("t", "test"):
    @bot.command(name = cmd)
    async def test(ctx):
        print(queues)


bot.run(settings['token'])
