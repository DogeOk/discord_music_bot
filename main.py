import discord
from discord.ext import commands
from discord import app_commands
from discord import FFmpegPCMAudio
from discord import Embed
from os import listdir, system, rmdir, remove
from os.path import isfile, join
from threading import Thread
from settings import settings
from subprocess import check_output
from server_info import ServerInfo

queues = {}
now_playing = {}
server_info_dict = {}

def check_queue(server_info, voice, station):
    if (len(server_info.queue) != 0):
        voice.play(
            FFmpegPCMAudio(f"./music/{station}/{server_info.queue[0]}"),
            after = lambda x = None: check_queue(server_info, voice, station)
        )
        server_info.now_playing = server_info.song_names[0]
        del server_info.queue[0]
        del server_info.song_names[0]


def check_play(ctx):
    guild_id = ctx.message.guild.id
    voice = ctx.guild.voice_client
    files = [f for f in listdir(f"./yt/{guild_id}") if isfile(join(f"./yt/{guild_id}", f))]
    for file_name in files:
        remove(f"./yt/{guild_id}/{file_name}")
    if (guild_id in queues):
        if (len(queues[guild_id]["playlist"]) != 0):
            link = queues[guild_id]["playlist"][0][0]
            playlist_counter = queues[guild_id]["playlist"][0][1]
            system(f"yt-dlp -f bestaudio --playlist-items \"{playlist_counter}\" -o \"./yt/{guild_id}/%(title)s.%(ext)s\" \"{link}\"")
            path = f"./yt/{guild_id}/" + listdir(f"./yt/{guild_id}")[0]
            voice.play(FFmpegPCMAudio(path), after = lambda x = None: check_play(ctx))
            del queues[guild_id]["playlist"][0]
            now_playing[guild_id] = queues[guild_id]["song_name"][0]
            del queues[guild_id]["song_name"][0]
        else:
            del queues[guild_id]
            rmdir(f"./yt/{guild_id}/")


def check_link(guild_id, link, is_playlist):
    if (is_playlist == None):
        is_playlist = check_playlist(link)
    if (not is_playlist):
        song_name = check_output(f"yt-dlp --no-warnings --ignore-errors --simulate --get-title {link}", shell=True).decode("windows_1251")[:-1]
        queues[guild_id]["playlist"].append([link, 1])
        queues[guild_id]["song_name"].append(song_name)
    else:
        song_names = check_output(f"yt-dlp --no-warnings --ignore-errors --simulate --get-title {link}", shell=True).decode("windows_1251").split("\n")[:-1]
        i = 1
        for song_name in song_names:
            queues[guild_id]["playlist"].append([link, i])
            queues[guild_id]["song_name"].append(song_name)
            i += 1


def check_playlist(link):
    return False
    return len(check_output(f"yt-dlp --playlist-items \"1, 2\" --simulate --get-id {link}", shell=True).decode("windows_1251").split("\n")[:-1]) > 1


bot = commands.Bot(
    command_prefix = settings['prefix'],
    help_command = None,
    intents=discord.Intents.all()
)

@bot.event
async def on_ready():
    await bot.change_presence(activity = discord.Game(name = f"{settings['prefix']}help"))


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
            yt_play_thread = Thread(target = check_play, args = (ctx,))
            yt_play_thread.start()


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
        if (queues[guild_id] == None):
            return
        message = ctx.message.content.split(' ')
        if (len(message) >= 2):
            n = int(message[1])
        else:
            n = 1
        range_param = 10 * n
        if n == len(queues[guild_id]["song_name"]) // 10 + 1:
            range_param = len(queues[guild_id]["song_name"])
        text = f"Сейчас играет: {now_playing[guild_id]}\n"
        if (len(queues[guild_id]["song_name"]) != 0):
            text += "Следующие треки:\n"
            for i in range(10 * (n - 1), range_param):
                text += f"{i + 1}. {queues[guild_id]['song_name'][i]} \n"
            text += f"Страница {n} из {len(queues[guild_id]['song_name']) // 10 + 1}"
        await ctx.send(text)

@bot.tree.command(name="queue", description = "Выводит список песен")
async def queue_slash(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if (queues[guild_id] == None):
        return
    n = 1
    range_param = 10 * n
    if n == len(queues[guild_id]["song_name"]) // 10 + 1:
        range_param = len(queues[guild_id]["song_name"])
    text = f"Сейчас играет: {now_playing[guild_id]}\n"
    if (len(queues[guild_id]["song_name"]) != 0):
        text += "Следующие треки:\n"
        for i in range(10 * (n - 1), range_param):
            text += f"{i + 1}. {queues[guild_id]['song_name'][i]} \n"
        text += f"Страница {n} из {len(queues[guild_id]['song_name']) // 10 + 1}"
    await interaction.response.send_message(text)

@bot.tree.command(name="radio", description = "Запускает радио")
@app_commands.choices(station=[
    discord.app_commands.Choice(name="music", value="music"),
    discord.app_commands.Choice(name="♂️gachi♂️", value="gachi")
])
async def radio(interaction: discord.Interaction, station: discord.app_commands.Choice[str]):
    server_info_dict[interaction.guild_id] = ServerInfo()
    server_info = server_info_dict[interaction.guild_id]
    voice = interaction.guild.voice_client
    if (interaction.user.voice is None):
        await interaction.response.send_message("Необходимо быть в голосовом канале, чтобы использовать эту команду.")
        return
    if (voice == None):
        await interaction.user.voice.channel.connect()
        voice = interaction.guild.voice_client
    else:
        return
    server_info.queue = [f for f in listdir(f"./music/{station.value}") if isfile(join(f"./music/{station.value}", f))]
    server_info.song_names = server_info.queue[:]
    await interaction.response.send_message(f"Запускаю радио")#, view = Buttons())
#    server_info.player_message_id = player_message.id
    server_info.shuffle_queue()
    check_queue(server_info, voice, station.value)


class Buttons(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
    
    @discord.ui.button(label="play", style=discord.ButtonStyle.gray)
    async def play_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        voice = interaction.guild_id.voice_client
        voice.resume()
    
    @discord.ui.button(label="pause", style=discord.ButtonStyle.gray)
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        voice = interaction.guild_id.voice_client
        voice.pause()

    @discord.ui.button(label="leave", style=discord.ButtonStyle.gray)
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild_id
        if (guild_id in queues):
            del queues[guild_id]
            interaction.guild.voice_client.stop()
        await interaction.guild.voice_client.disconnect()
        await interaction.response.defer()
        await interaction.message.delete()
    
    @discord.ui.button(label="test", style=discord.ButtonStyle.gray)
    async def test_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.message.edit(content = "test", view = Buttons())
        print(interaction.message.id)


@bot.tree.command(name="player", description = "Вызов музыкального плеера")
async def player(interaction: discord.Interaction):
    server_info_dict[interaction.guild_id] = ServerInfo()
    await interaction.response.send_message(f"Интерактивный плеер", view = Buttons())



@bot.command()
async def sync(ctx):
    await bot.tree.sync()
    bot.tree.copy_global_to(guild=discord.Object(id=325364575346229269))


@bot.command()
async def test(ctx):
    embed = Embed(title="Title", description="Description", url="https://www.google.com")
    embed.add_field(name="name", value="value")
    embed.add_field(name="name", value="value")
    embed.add_field(name="name", value="value")
    embed.add_field(name="name", value="value")
    await ctx.send(embed=embed)

bot.run(settings['token'])
