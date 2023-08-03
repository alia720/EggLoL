# EggLoL

import discord
import aiohttp
import configparser
import psycopg2
import lxml
import simplejson as json
from psycopg2 import Error
from bs4 import BeautifulSoup
from typing import Optional
from discord import app_commands
from discord.ext import commands

# Read .ini file

cfg = configparser.ConfigParser()

cfg.read("main/keys.ini")

# Connect to PostgreSQL database

try:

    conn = psycopg2.connect(

        host = cfg.get("PostgreSQL", "Host"),
        database = cfg.get("PostgreSQL", "Database"),
        port = cfg.get("PostgreSQL", "Port"),
        user = cfg.get("PostgreSQL", "Username"),
        password = cfg.get("PostgreSQL", "Password")

    )

except (Exception, Error) as error:

    print(f"An error occured while trying to connect to PostgreSQL: {error}")

# Synchronous functions

def embed_error(msg):

    return discord.Embed(title = "Error(s)", description = f"{msg}", color = 0xff0000)

def query(query):

    with conn.cursor() as cursor:

        cursor.execute(query)

        return cursor.fetchone()
    
def check_champ(champ_name):

    with open("main/champs.json") as file:

        champs = json.load(file)

    champs_list = list(map(str.lower, champs["champs_list"]))

    champs_for_url = list(map(str.lower, champs["champs_for_url"].keys()))

    if champ_name.lower() not in champs_list and champ_name not in champs_for_url:

        return f"* **{champ_name}** is not a champion in League of Legends.\n"
    
    return ""
    
# Asynchronous functions

async def aio_get_soup(url):

    async with aiohttp.ClientSession(headers = {"User-Agent": "Mozilla/5.0"}) as session:

        async with session.get(url = url) as response:

            resp = await response.text()

            return BeautifulSoup(resp, "lxml")
        
async def get_champion_stats(champion_name):

    with open("main/champs.json") as file:

        champs_for_url = json.load(file)["champs_for_url"]

    if champion_name in champs_for_url.keys():

        champion_name = champs_for_url[champion_name]

    url = f"https://u.gg/lol/champions/{champion_name}/build"

    soup = await aio_get_soup(url)

    try:

        tier = soup.find("div", "champion-ranking-stats-normal").find("div","tier value okay-tier").text
        winrate = soup.find("div", "champion-ranking-stats-normal").find("div","win-rate okay-tier").div.text
        overallrank = soup.find("div", "champion-ranking-stats-normal").find("div","overall-rank").div.text
        pickrate = soup.find("div", "champion-ranking-stats-normal").find("div","pick-rate").div.text
        banrate = soup.find("div", "champion-ranking-stats-normal").find("div","ban-rate").div.text
        totalmatches = soup.find("div", "champion-ranking-stats-normal").find("div","matches").div.text

        return {

            "Champion": champion_name,
            "Tier": tier,
            "Win Rate": winrate,
            "Rank": overallrank,
            "Pick Rate": pickrate,
            "Ban Rate": banrate,
            "Matches": totalmatches,

        }
    
    except AttributeError:

        print(f"Error: Data not found for {champion_name}.")
        return None

# Bot initialization

TOKEN = cfg.get("Discord", "BotToken")

bot = commands.Bot(command_prefix = ".", intents = discord.Intents.all())

# Bot

@bot.event
async def on_ready():

    try:
        
        synced = await bot.tree.sync()
        print(f"Succesfully synced {len(synced)} command(s)!")

    except Exception as e:

        print(e)

    print(f"{bot.user.name} is online!")

    await bot.change_presence(status = discord.Status.online, activity= discord.Game("/help"))

@bot.tree.command(name = "help", description = "Get an overview of all the commands and how to use them.")
async def help(interaction: discord.Interaction):

    await interaction.response.defer(ephemeral = False)
    #

    embed = discord.Embed(title = "Test", color = 0xE8E1E1)

    #
    await interaction.followup.send(embed = embed, ephemeral = False)
    return

@bot.tree.command(name = "set_profile", description = "For a more tailored experience, set up your LoL profile!")
@app_commands.describe(region = "Your matchmaking region.", username = "Your LoL username.", main_champion = "Your main champion (if you don't main one champion, put your most played champion)")
@app_commands.choices(region = [

    app_commands.Choice(name = "NA", value = "NA"),
    app_commands.Choice(name = "EUW", value = "EUW"),
    app_commands.Choice(name = "KR", value = "KR"),
    app_commands.Choice(name = "BR", value = "BR"),
    app_commands.Choice(name = "EUN", value = "EUN"),
    app_commands.Choice(name = "JP", value = "JP"),
    app_commands.Choice(name = "LAN", value = "LAN"),
    app_commands.Choice(name = "LAS", value = "LAS"),
    app_commands.Choice(name = "OCE", value = "OCE"),
    app_commands.Choice(name = "RU", value = "RU"),
    app_commands.Choice(name = "TR", value = "TR"),
    app_commands.Choice(name = "PH", value = "PH"),
    app_commands.Choice(name = "SG", value = "SG"),
    app_commands.Choice(name = "TH", value = "TH"),
    app_commands.Choice(name = "TW", value = "TW"),
    app_commands.Choice(name = "VN", value = "VN")

])

async def setProfile(interaction: discord.Interaction, region: app_commands.Choice[str], username: str, main_champion: str):

    await interaction.response.defer(ephemeral = False)
    #

    with open("main/regions.json") as file:

        regions = json.load(file)

    user_url = f"https://u.gg/lol/profile/{regions[region.value]}/{username}/overview"

    profile_soup = await aio_get_soup(user_url)

    error_msg = ""

    try:

        name = profile_soup.find("div", "summoner-name").text

    except AttributeError as e:

        error_msg += f"* The username **{username}** was not found in the **{region.value}** region. *Try another region or double-check the username*.\n"


    error_msg += check_champ(main_champion)

    if error_msg != "":

        await interaction.followup.send(embed = embed_error(error_msg))
        return

    rank = profile_soup.find("span", "unranked").text
    lp = ""

    if rank  == "":

        rank = profile_soup.find("div", "rank-text").span.text
        lp = profile_soup.find("div", "rank-text").find_all("span")[1].text

    #
    await interaction.followup.send(f"Region: {region.value}\nUsername: {username}\nMain: {main_champion}\nRank: {rank} {lp}")



bot.run(TOKEN)