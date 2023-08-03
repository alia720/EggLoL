# EggLoL

import discord
import aiohttp
import configparser
import psycopg2
import lxml
import simplejson as json
from uuid_extensions import uuid7
from psycopg2 import Error
from psycopg2 import IntegrityError
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

    print("Successfully connected to Postgres server!")

except (Exception, Error) as error:

    print(f"An error occured while trying to connect to PostgreSQL: {error}")

# Synchronous functions

def embed_error(msg):

    return discord.Embed(title = "Error(s)", description = f"{msg}", color = 0xff0000)

def query(query):

    try:

        with conn.cursor() as cursor:

            cursor.execute(query)
            conn.commit()

            return 200
        
    except IntegrityError as e:

        return 409
    
def get_champs_json():

    with open("main/champs.json") as file:

        champs = json.load(file)

    champs_list = list(champs["champs_list"])
    champs_for_url = list(champs["champs_for_url"].keys())

    return champs_list, champs_for_url
    
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

async def setProfile(interaction: discord.Interaction, region: app_commands.Choice[str], username: app_commands.Range[str, 3, 16], main_champion: app_commands.Range[str, 3, 14]):

    await interaction.response.defer(ephemeral = False)
    #

    region = region.value

    with open("main/regions.json") as file:

        regions = json.load(file)

    user_url = f"https://u.gg/lol/profile/{regions[region]}/{username}/overview"

    profile_soup = await aio_get_soup(user_url)

    error_msg = ""

    try:

        username_char_corrected = profile_soup.find("div", "summoner-name").text

    except AttributeError as e:

        error_msg += f"* The username **{username}** was not found in the **{region}** region. *Try another region or double-check the username*.\n"

    champs_list, champs_for_url = get_champs_json()

    champs_list_lowered = list(map(str.lower, champs_list))
    champs_for_url_lowered = list(map(str.lower, champs_for_url))

    if main_champion.lower() not in champs_list_lowered and main_champion.lower() not in champs_for_url_lowered:

        error_msg += f"* **{main_champion}** is not a champion in League of Legends.\n"

    if error_msg != "":

        await interaction.followup.send(embed = embed_error(error_msg))
        return
    
    # Checkpoint | username and main_champion have been verified 

    rank = profile_soup.find("span", "unranked").text
    lp = ""

    if rank  == "":

        rank = profile_soup.find("div", "rank-text").span.text
        lp = profile_soup.find("div", "rank-text").find_all("span")[1].text

    # Checkpoint | rank has been retrieved

    all_champs = champs_list + champs_for_url
    all_champs_lowered = champs_list_lowered + champs_for_url_lowered

    champ_index = all_champs_lowered.index(main_champion.lower())

    main_champion_char_corrected = all_champs[champ_index]

    # Checkpoint | main_champion has been character corrected

    uuid = uuid7()

    initial_query_resp = query(f"INSERT INTO discord_user (discord_user_id) VALUES ({interaction.user.id});")

    if initial_query_resp == 409:

        await interaction.followup.send(embed = embed_error("* You have already set up a profile, try updating it instead."))
        return

    query(f"INSERT INTO lol_profile (profile_uuid, region, username, main_champion, rank) VALUES ('{uuid}', '{region}', '{username_char_corrected}', '{main_champion_char_corrected}', '{rank} {lp}');")

    query(f"UPDATE discord_user SET profile_uuid = '{uuid}' WHERE discord_user_id = {interaction.user.id}")

    #
    
    await interaction.followup.send(f"Region: {region}\nUsername: {username}\nMain: {main_champion_char_corrected}\nRank: {rank} {lp}")



bot.run(TOKEN)