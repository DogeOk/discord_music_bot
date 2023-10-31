import discord
from discord.ext import commands
from discord import app_commands
from discord import FFmpegPCMAudio
import lyricsgenius
from os import listdir, system, rmdir, remove
from os.path import isfile, join
import os
from threading import Thread
from settings import settings
from subprocess import check_output
from server_info import ServerInfo

queues = {}
now_playing = {}
server_info_dict = {}
genius = lyricsgenius.Genius(settings["genius-token"])
bot = commands.Bot(
    command_prefix=settings['prefix'],
    help_command=None,
    intents=discord.Intents.all()
)


def check_queue(server_info, voice, station):
    if (len(server_info.queue) != 0):
        voice.play(
            FFmpegPCMAudio(f"./music/{station}/{server_info.queue[0]}"),
            after=lambda x=None: check_queue(server_info, voice, station)
        )
        server_info.now_playing = server_info.song_names[0]
        del server_info.queue[0]
        del server_info.song_names[0]


def check_play(interaction):
    guild_id = interaction.guild_id
    voice = interaction.guild.voice_client
    newpath = f"./yt/{guild_id}"
    if not os.path.exists(newpath):
        os.makedirs(newpath)
    files = [
        f for f in listdir(
            f"./yt/{guild_id}"
        ) if isfile(join(f"./yt/{guild_id}", f))
    ]
    for file_name in files:
        remove(f"./yt/{guild_id}/{file_name}")
    if (guild_id in queues):
        if (len(queues[guild_id]["playlist"]) != 0):
            link = queues[guild_id]["playlist"][0][0]
            playlist_counter = queues[guild_id]["playlist"][0][1]
            system(f"yt-dlp -f bestaudio --playlist-items \"{playlist_counter}\" -o \"./yt/{guild_id}/%(title)s.%(ext)s\" \"{link}\"")
            path = f"./yt/{guild_id}/" + listdir(f"./yt/{guild_id}")[0]
            voice.play(
                FFmpegPCMAudio(path),
                after=lambda x=None: check_play(interaction)
            )
            del queues[guild_id]["playlist"][0]
            now_playing[guild_id] = queues[guild_id]["song_name"][0]
            del queues[guild_id]["song_name"][0]
        else:
            del queues[guild_id]
            rmdir(f"./yt/{guild_id}/")


def check_link(guild_id, link, is_playlist):
    if (is_playlist is None):
        is_playlist = check_playlist(link)
    if (not is_playlist):
        song_name = check_output(f"yt-dlp --no-warnings --ignore-errors --simulate --get-title {link}", shell=True).decode("windows_1251")[:-1]
        queues[guild_id]["playlist"].append([link, 1])
        queues[guild_id]["song_name"].append(song_name)
    else:
        song_names = check_output(
            f"yt-dlp --no-warnings --ignore-errors --simulate --get-title {link}",
            shell=True).decode("windows_1251").split("\n")[:-1]
        i = 1
        for song_name in song_names:
            queues[guild_id]["playlist"].append([link, i])
            queues[guild_id]["song_name"].append(song_name)
            i += 1


def check_playlist(link):
    return False
    return len(
        check_output(
            f"yt-dlp --playlist-items \"1, 2\" --simulate --get-id {link}",
            shell=True
        ).decode("windows_1251").split("\n")[:-1]) > 1


@bot.tree.command(name="play", description="Запуск песен из youtube")
@app_commands.describe(link="Ссылка на видео")
async def play(
    interaction: discord.Interaction,
    link: str
):
    guild_id = interaction.guild_id
    voice = interaction.guild.voice_client
    await interaction.response.send_message("Playing...")
    if (voice is None):
        await interaction.user.voice.channel.connect()
    if (guild_id in queues):
        if (queues[guild_id]["play_mode"] == "radio"):
            return
        check_link_thread = Thread(
            target=check_link,
            args=(guild_id, link, None)
        )
        check_link_thread.start()
    else:
        queues[guild_id] = {}
        queues[guild_id]["playlist"] = []
        queues[guild_id]["song_name"] = []
        queues[guild_id]["play_mode"] = "yt"
        check_link(guild_id, link, None)
        yt_play_thread = Thread(target=check_play, args=(interaction,))
        yt_play_thread.start()


@bot.tree.command(name="skip", description="Пропуск песен")
@app_commands.describe(n="Количество песен")
async def skip(
    interaction: discord.Interaction,
    n: str
):
    server_info = server_info_dict[interaction.guild_id]
    if n.isdigit():
        n = int(n)
    else:
        n = 1
    del server_info.queue[:n-1]
    del server_info.song_names[:n-1]
    interaction.guild.voice_client.stop()
    print(str(n)[-1])
    if str(n)[-1] == '1':
        await interaction.response.send_message(f"Пропускаю {n} песню")
    elif str(n)[-1] in ['2', '3', '4']:
        await interaction.response.send_message(f"Пропускаю {n} песни")
    else:
        await interaction.response.send_message(f"Пропускаю {n} песен")


@bot.tree.command(name="queue", description="Выводит список песен")
async def queue_slash(interaction: discord.Interaction):
    server_info = server_info_dict[interaction.guild_id]
    if (server_info.queue is None):
        await interaction.response.send_message("Вы не запустили радио")
        return
    n = 1
    range_param = 10 * n
    if n == len(server_info.song_names) // 10 + 1:
        range_param = len(server_info.song_names)
    text = f"Сейчас играет: {server_info.now_playing}\n"
    if (len(server_info.song_names) != 0):
        text += "Следующие треки:\n"
        for i in range(10 * (n - 1), range_param):
            text += f"{i + 1}. {server_info.song_names[i]} \n"
        text += f"Страница {n} из {len(server_info.song_names) // 10 + 1}"
    await interaction.response.send_message(text)


@bot.tree.command(name="radio", description="Запускает радио")
@app_commands.choices(station=[
    discord.app_commands.Choice(name="music", value="music"),
    discord.app_commands.Choice(name="♂️gachi♂️", value="gachi"),
    discord.app_commands.Choice(name="Audio attack", value="au")
])
async def radio(
    interaction: discord.Interaction,
    station: discord.app_commands.Choice[str]
):
    server_info_dict[interaction.guild_id] = ServerInfo()
    server_info = server_info_dict[interaction.guild_id]
    voice = interaction.guild.voice_client
    if (interaction.user.voice is None):
        await interaction.response.send_message(
            "Зайдите в голсовой канал"
        )
        return
    if (voice is None):
        await interaction.user.voice.channel.connect()
        voice = interaction.guild.voice_client
    else:
        return
    server_info.queue = [
        f for f in listdir(
            f"./music/{station.value}"
        ) if isfile(join(f"./music/{station.value}", f))
    ]
    server_info.song_names = server_info.queue[:]
    await interaction.response.send_message("Запускаю радио")
    server_info.shuffle_queue()
    check_queue(server_info, voice, station.value)


@bot.tree.command(
    name="resume",
    description="Возобновить воспроизведение песен"
)
async def play_button(interaction: discord.Interaction):
    await interaction.response.send_message("Возбновляю воспроизведение песен")
    voice = interaction.guild_id.voice_client
    voice.resume()


@bot.tree.command(name="pause", description="Пауза")
async def pause_button(interaction: discord.Interaction):
    await interaction.response.send_message("Ставлю песни на паузу")
    voice = interaction.guild_id.voice_client
    voice.pause()


@bot.tree.command(name="lyrics", description="Вывести текст песни")
async def lyrics(interaction: discord.Interaction):
    server_info = server_info_dict[interaction.guild_id]
    song_name = server_info.now_playing.replace('.mp3', '').replace('.webm', '')
    try:
        song = genius.search_song(song_name)
        song_lyrics = song.lyrics[song.lyrics.find("Lyrics")+6:-5]
        embed = discord.Embed(
            title=song_name,
            description=song_lyrics,
            color=discord.Color.blue(),
            url=song.url
        )
        embed.set_thumbnail(url=song.song_art_image_thumbnail_url)
        if len(song_lyrics) < 4096:
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Я не смог найти песню или в ней нет слов")
    except AttributeError:
        await interaction.response.send_message("Я не смог найти песню или в ней нет слов")


@bot.tree.command(
    name="leave",
    description="Выкинуть бота из голосового канала"
)
async def leave_button(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if (guild_id in queues):
        del queues[guild_id]
        interaction.guild.voice_client.stop()
    await interaction.guild.voice_client.disconnect()
    await interaction.response.send_message("Улетучиваюсь")


@bot.command()
async def sync(ctx):
    await bot.tree.sync()
    bot.tree.copy_global_to(guild=discord.Object(id=325364575346229269))

bot.run(settings['token'])
