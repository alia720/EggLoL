# EggLoL

import discord
import aiohttp
import configparser
from bs4 import BeautifulSoup
from typing import Optional
from discord import app_commands
from discord.ext import commands

cfg = configparser.ConfigParser()

cfg.read("main/keys.ini")

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

bot.run(TOKEN)