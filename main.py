import discord
from discord.ext import commands
from discord import app_commands
from discord import FFmpegPCMAudio
import lyricsgenius
from os import listdir, system
from os.path import isfile, join
from settings import settings
from subprocess import check_output
from server_info import ServerInfo, SongInfo
import shutil
import os
from threading import Thread


server_info_dict = {}
genius = lyricsgenius.Genius(settings["genius-token"])
bot = commands.Bot(
    command_prefix=settings['prefix'],
    help_command=None,
    intents=discord.Intents.all()
)


def check_queue(server_info, voice):
    guild_id = server_info.guild_id
    if (len(server_info.songs) != 0):
        server_info.now_playing = server_info.songs[0]
        del server_info.songs[0]
        if (server_info.now_playing.link_type == "file"):
            voice.play(
                FFmpegPCMAudio(server_info.now_playing.link),
                after=lambda x=None: check_queue(server_info, voice)
            )
        else:
            newpath = f"./yt/{guild_id}"
            if not os.path.exists(newpath):
                os.makedirs(newpath)
            link = server_info.now_playing.link
            shutil.rmtree(f"./yt/{guild_id}")
            system(f"yt-dlp -f bestaudio -o \"./yt/{guild_id}/%(title)s.%(ext)s\" \"{link}\"")
            path = f"./yt/{guild_id}/" + listdir(f"./yt/{guild_id}")[0]
            voice.play(
                FFmpegPCMAudio(path),
                after=lambda x=None: check_queue(server_info, voice)
            )
    else:
        server_info.now_playing = None


@bot.tree.command(name="play", description="Запуск песен из youtube")
@app_commands.describe(link="Ссылка на видео")
async def play(
    interaction: discord.Interaction,
    link: str
):
    voice = interaction.guild.voice_client
    if (interaction.user.voice is None):
        await interaction.response.send_message(
            "Зайдите в голсовой канал"
        )
        return
    if server_info_dict.get(interaction.guild_id) is None:
        server_info_dict[interaction.guild_id] = ServerInfo(interaction.guild_id)
    server_info = server_info_dict[interaction.guild_id]
    await interaction.response.send_message("Играю...")
    song_name = check_output(f"yt-dlp --no-warnings --ignore-errors --simulate --get-title \"{link}\"", shell=True).decode("windows_1251")[:-1]
    server_info.songs.append(SongInfo(link, "url", song_name))
    if (voice is None):
        await interaction.user.voice.channel.connect()
        voice = interaction.guild.voice_client
        play_thread = Thread(target=check_queue, args=(server_info, voice))
        play_thread.start()


@bot.tree.command(name="skip", description="Пропуск песен")
@app_commands.describe(songs="Количество песен")
async def skip(
    interaction: discord.Interaction,
    songs: str
):
    server_info = server_info_dict[interaction.guild_id]
    if songs.isdigit():
        songs = int(songs)
    else:
        songs = 1
    del server_info.songs[:songs-1]
    interaction.guild.voice_client.stop()
    if str(songs)[-1] == '1':
        await interaction.response.send_message(f"Пропускаю {songs} песню")
    elif str(songs)[-1] in ['2', '3', '4']:
        await interaction.response.send_message(f"Пропускаю {songs} песни")
    else:
        await interaction.response.send_message(f"Пропускаю {songs} песен")


@bot.tree.command(name="queue", description="Выводит список песен")
@app_commands.describe(page="Номер страницы")
async def queue_slash(
    interaction: discord.Interaction,
    page: str
):
    server_info = server_info_dict[interaction.guild_id]
    if (server_info.songs is None):
        await interaction.response.send_message("Вы не запустили радио")
        return
    if page.isdigit():
        page = int(page)
    else:
        page = 1
    range_param = 10 * page
    if page == len(server_info.songs) // 10 + 1:
        range_param = len(server_info.songs)
    text = f"Сейчас играет: {server_info.now_playing.song_name}\n"
    if (len(server_info.songs) != 0):
        text += "Следующие треки:\n"
        for i in range(10 * (page - 1), range_param):
            text += f"{i + 1}. {server_info.songs[i].song_name} \n"
        text += f"Страница {page} из {len(server_info.songs) // 10 + 1}"
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
    voice = interaction.guild.voice_client
    if (interaction.user.voice is None):
        await interaction.response.send_message(
            "Зайдите в голсовой канал"
        )
        return
    if server_info_dict.get(interaction.guild_id) is None:
        server_info_dict[interaction.guild_id] = ServerInfo(interaction.guild_id)
    server_info = server_info_dict[interaction.guild_id]
    if (voice is None):
        await interaction.user.voice.channel.connect()
        voice = interaction.guild.voice_client
    for f in [f for f in listdir(f"./music/{station.value}") if isfile(join(f"./music/{station.value}", f))]:
        server_info.songs.append(SongInfo(join(f"./music/{station.value}", f), "file", f.replace('.mp3', '').replace('.webm', '')))
    if server_info.now_playing is None:
        server_info.shuffle_queue()
        play_thread = Thread(target=check_queue, args=(server_info, voice))
        play_thread.start()
        await interaction.response.send_message("Запускаю радио")
        return
    await interaction.response.send_message("Добавил радио")


@bot.tree.command(
    name="shuffle",
    description="Перемешать плейлист"
)
async def shuffle(interaction: discord.Interaction):
    if server_info_dict.get(interaction.guild_id) is None:
        server_info_dict[interaction.guild_id] = ServerInfo(interaction.guild_id)
    server_info = server_info_dict[interaction.guild_id]
    server_info.shuffle_queue()
    await interaction.response.send_message("Перемешиваю плейлист")


@bot.tree.command(
    name="resume",
    description="Возобновить воспроизведение песен"
)
async def play_button(interaction: discord.Interaction):
    await interaction.response.send_message("Возбновляю воспроизведение песен")
    voice = interaction.guild.voice_client
    voice.resume()


@bot.tree.command(name="pause", description="Пауза")
async def pause_button(interaction: discord.Interaction):
    await interaction.response.send_message("Ставлю песни на паузу")
    voice = interaction.guild.voice_client
    voice.pause()


@bot.tree.command(name="lyrics", description="Вывести текст песни")
async def lyrics(interaction: discord.Interaction):
    server_info = server_info_dict[interaction.guild_id]
    song_name = server_info.now_playing.song_name
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
    server_info_dict[interaction.guild_id].songs = []
    await interaction.guild.voice_client.disconnect()
    await interaction.response.send_message("Улетучиваюсь")


@bot.command()
async def sync(ctx):
    await bot.tree.sync()
    bot.tree.copy_global_to(guild=discord.Object(id=325364575346229269))

bot.run(settings['token'])
