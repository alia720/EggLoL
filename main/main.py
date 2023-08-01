# EggLoL

import discord
import aiohttp
import configparser
import psycopg2
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

# Functions

def query(query):

    with conn.cursor() as cursor:

        cursor.execute(query)

        return cursor.fetchone()

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

    embed = discord.Embed(title = "Test", color = 0xE8E1E1)

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

    await interaction.followup.send(f"Region: {region}\nUsername: {username}\nMain: {main_champion}\n{query('SELECT * FROM discord_user;')}")

bot.run(TOKEN)