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

    conn.autocommit = True

    print("Successfully connected to Postgres server!")

except (Exception, Error) as error:

    print(f"An error occured while trying to connect to PostgreSQL: {error}")

# Synchronous functions

def embed_error(msg):

    return discord.Embed(title = "Error(s)", description = f"{msg}", color = 0xff0000)

def query_mainpulate_data(query):

    try:

        with conn.cursor() as cursor:

            cursor.execute(query)

            return 200
        
    except:

        return 409
    
def query_get_data(query):

    try:

        with conn.cursor() as cursor:

            cursor.execute(query)

            return cursor.fetchone()
        
    except:

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

    main_champion_for_ui = all_champs[champ_index]
    main_champion_for_db = main_champion_for_ui.replace("'", '"')

    # Checkpoint | main_champion has been character corrected

    uuid = uuid7()
    discord_user_id = interaction.user.id

    initial_query_resp = query_mainpulate_data(f"INSERT INTO discord_user (discord_user_id) VALUES ({discord_user_id});")

    if initial_query_resp == 409:

        try:

            profile_uuid = query_get_data(f"SELECT profile_uuid FROM discord_user WHERE discord_user_id = {discord_user_id}")[0]
            lol_profile_data = query_get_data(f"SELECT region, username, main_champion, rank FROM lol_profile WHERE profile_uuid = '{profile_uuid}'")

        except:

            await interaction.followup.send(embed = embed_error("* Something went wrong while updating your profile. Try again later."))
            return

        enetered_data_tuple = (region, username_char_corrected, main_champion_for_db, f"{rank} {lp}")

        if enetered_data_tuple == lol_profile_data:

            embed = discord.Embed(title = "Your current profile already matches what you entered...", color = 0xFFA63B)
            await interaction.followup.send(embed = embed)
            return

        query_mainpulate_data(f"UPDATE lol_profile SET region = '{region}', username = '{username_char_corrected}', main_champion = '{main_champion_for_db}', rank = '{rank} {lp}' WHERE profile_uuid = '{profile_uuid}';")

        embed = discord.Embed(title = "Profile has been updated!", description = f"__Your new profile__:\n\n**Region**: {region}\n**Username**: {username_char_corrected}\n**Main Champion**: {main_champion_for_ui}\n**Rank**: {rank} {lp}", color = 0x00AA00)
        await interaction.followup.send(embed = embed)
        return

    query_mainpulate_data(f"INSERT INTO lol_profile (profile_uuid, region, username, main_champion, rank) VALUES ('{uuid}', '{region}', '{username_char_corrected}', '{main_champion_for_db}', '{rank} {lp}');")
    query_mainpulate_data(f"UPDATE discord_user SET profile_uuid = '{uuid}' WHERE discord_user_id = {discord_user_id}")

    #
    
    embed = discord.Embed(title = "Profile has been created!", description = f"__Your new profile__:\n\n**Region**: {region}\n**Username**: {username_char_corrected}\n**Main Champion**: {main_champion_for_ui}\n**Rank**: {rank} {lp}", color = 0x00AA00)
    await interaction.followup.send(embed = embed)
    return

@bot.tree.command(name = "champion_stats", description = "Lookup a champion for more info!")
@app_commands.describe(champion_name = "Champion name for info")
async def champion_stats(interaction: discord.Interaction, champion_name: str):

    await interaction.response.defer(ephemeral = False)


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
    
    except AttributeError:

        print(f"Error: Data not found for {champion_name}.")
        return None
    
    await interaction.followup.send(f"Champion: {champion_name}\nTier: {tier}\nWin Rate: {winrate}\nRank: {overallrank}\nPick Rate: {pickrate}\nBan Rate: {banrate}\nMatches: {totalmatches}")

bot.run(TOKEN)