# EggLoL

import discord
import aiohttp
import configparser
import psycopg2
import simplejson as json
from uuid_extensions import uuid7
from psycopg2 import Error
from bs4 import BeautifulSoup
from typing import Optional
from types import SimpleNamespace
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

        return 400
    
def query_get_data(query):

    try:

        with conn.cursor() as cursor:

            cursor.execute(query)

            return cursor.fetchone()
        
    except:

        return 400
    
def get_champions_json(choice):

    with open("main/champions.json") as file:

        champions = json.load(file)

    if choice == 1:

        return list(champions["champions_list"]) + list(champions["champions_for_url"].keys())

    elif choice == 2:

        champions_list = list(champions["champions_list"])
        champions_for_url = champions["champions_for_url"]

        return champions_list, champions_for_url

    elif choice == 3:

        return champions["champions_for_url"]

def lower_list(list_to_lower):

    return list(map(str.lower, list_to_lower))

def is_valid_champion(champion_name):

    all_champions_lowered = lower_list(get_champions_json(1))

    if champion_name.lower() not in all_champions_lowered:

        return False
    
    else:

        return True
    
def get_champion_for_ui(champion_name):

    all_champions = get_champions_json(1)

    all_champions_lowered = lower_list(all_champions)

    champ_index = all_champions_lowered.index(champion_name.lower())

    return all_champions[champ_index]

def get_champion_for_url(champion_name):

    champions_for_url = get_champions_json(3)

    for key, value in champions_for_url.items():

        if key.lower() == champion_name.lower():

            return value
        
    return champion_name

def get_region_for_url(region):

    with open("main/regions.json") as file:

        regions = json.load(file)

    return regions[region]

def get_emote(emote_for, key):

    with open("main/emote_mappings.json") as file:

        mappings = json.load(file)

    try:

        return mappings[emote_for][key]
    
    except:

        return "Not Found=:x:"

def create_url(interaction, champion_name, role, rank, queue_type, region):

    if isinstance(region, str):

        region_resp = query_get_data(f"SELECT region FROM discord_user JOIN lol_profile USING (profile_uuid) WHERE discord_user_id = {interaction.user.id}")

        if region_resp != 400 and region_resp != None:

            region = app_commands.Choice(name = region_resp[0], value = get_region_for_url(region_resp[0]))

        else:

            default_region_json = json.loads(region)

            region = SimpleNamespace(**default_region_json)

    if isinstance(queue_type, str):

        default_queue_json = json.loads(queue_type)

        queue_type = SimpleNamespace(**default_queue_json)

    error_msg = ""

    if queue_type.name == "ARAM" and role != None:

        error_msg += f"* **ARAM** game mode does not have roles!\n"

    if queue_type.name == "ARAM" and rank != '{"name": "Emerald +"}':

        error_msg += f"* **ARAM** game mode does not have ranks!\n"

    if (queue_type.name == "Normal Blind" or queue_type.name == "Normal Draft") and rank != '{"name": "Emerald +"}':

        error_msg += f"* **Normal** game modes do not have ranks!\n"

    if error_msg != "":

        url = None
        champion_name_for_ui = None
        rank = None
        queue_type = None
        region = None

        return url, champion_name_for_ui, rank, queue_type, region, error_msg

    if is_valid_champion(champion_name) == False:

        url = None
        champion_name_for_ui = None
        rank = None
        queue_type = None
        region = None
        error_msg += f"* **{champion_name}** is not a champion in League of Legends.\n"

        return url, champion_name_for_ui, rank, queue_type, region, error_msg

    champion_name_for_url = get_champion_for_url(champion_name)
    champion_name_for_ui = get_champion_for_ui(champion_name)

    if queue_type.name != "ARAM":

        url = f"https://u.gg/lol/champions/{champion_name_for_url}/build"

        if role != None:

            url += f"/{role.value}"

        url += "?"

        if isinstance(rank, str):

            default_rank_json = json.loads(rank)

            rank = SimpleNamespace(**default_rank_json)

        if rank.name != "Emerald +":

            url += f"rank={rank.value}&"

        if queue_type.name != "Ranked Solo/Duo":

            url += f"queueType={queue_type.value}&"

    else:

        url = f"https://u.gg/lol/champions/aram/{champion_name_for_url}-aram?"

    if type(region) != SimpleNamespace:

        url += f"region={region.value}&"

    return url, champion_name_for_ui, rank, queue_type, region, error_msg

def edit_skill_path_grid(div, skill_path_grid, row_index):

    row_mapping = {

        0: "<:q_:1142021169961259038>",
        1: "<:w_:1142021171278250064>",
        2: "<:e_:1142021173253779526>",
        3: "<:r_:1142021174415605811>" 

    }

    if "skill-up" in div["class"]:

        skill_path_grid += row_mapping[row_index]

    else: 

        skill_path_grid += "<:gs:1142000576721322077>"

    return skill_path_grid

def get_build_data(soup, champion_name_for_ui):

    try:

        runes_div = soup.find("div", "recommended-build_runes")
        primary_tree = runes_div.find("div", "primary-tree").find("div", "perk-style-title").text
        secondary_tree = runes_div.find("div", "secondary-tree").find("div", "perk-style-title").text
        runes = runes_div.find("div", "rune-trees-container-2 media-query media-query_MOBILE_LARGE__DESKTOP_LARGE").find_all("div", "perk-active")
        shards = runes_div.find("div", "rune-trees-container-2 media-query media-query_MOBILE_LARGE__DESKTOP_LARGE").find_all("div", "shard-active")
        runes_wr = runes_div.find("span", "win-rate").text
        runes_matches = runes_div .find("span", "matches").text

    except AttributeError:

        return {"Error": f"* No data was found for {champion_name_for_ui}!"}

    summoner_spells_div = soup.find("div", "summoner-spells")
    summoner_spells = summoner_spells_div.find_all("div", recursive = False)[1].find_all("img")
    summoner_spells_wr = summoner_spells_div.find("span", "win-rate").text
    summoner_spells_matches = summoner_spells_div.find("span", "matches").text

    skill_priority_div = soup.find("div", "skill-priority_content")
    skill_priority = skill_priority_div.find("div", "skill-priority-path").find_all("div", "skill-label")

    try:

        skill_priority_wr = skill_priority_div.find("div", "winrate").span.text
        skill_priority_matches = skill_priority_div.find("div", "matches").text

    except:

        skill_priority_wr = "~%"
        skill_priority_matches = "~ Matches"

    try:

        skill_path = soup.find("div", "skill-path-container")
        skill_path_rows = skill_path.find_all("div", "skill-order")[:4]

    except: 

        skill_path_rows = []

    recommended_build_items_div = soup.find("div", "recommended-build_items")

    starting_items = recommended_build_items_div.find("div", "starting-items").find_all("div", "item-img")
    starting_items_stats = recommended_build_items_div.find("div", "starting-items").find("div", "item-stats").div.text + " " + f"({recommended_build_items_div.find('div', 'starting-items').find('div', 'item-stats').find('div', 'matches').text})"
    core_items = recommended_build_items_div.find("div", "core-items").find_all("div", "item-img")

    try: 
        
        core_items_stats = recommended_build_items_div.find("div", "core-items").find("div", "item-stats").div.text + f"({recommended_build_items_div.find('div', 'core-items').find('div', 'item-stats').find('div', 'matches').text})"
    
    except:

        core_items_stats = ":x: Error Retrieving Core Items"

    fourth_item_options = recommended_build_items_div.find("div", "item-options-1").find_all("div", "item-img")
    fifth_item_options = recommended_build_items_div.find("div", "item-options-2").find_all("div", "item-img")
    sixth_item_options = recommended_build_items_div.find("div", "item-options-3").find_all("div", "item-img")

    return {

        "primary_tree": primary_tree,
        "secondary_tree": secondary_tree,
        "runes": runes,
        "shards": shards,
        "runes_wr": runes_wr,
        "runes_matches": runes_matches,
        "summoner_spells": summoner_spells,
        "summoner_spells_wr": summoner_spells_wr,
        "summoner_spells_matches": summoner_spells_matches,
        "skill_priority": skill_priority,
        "skill_priority_wr": skill_priority_wr,
        "skill_priority_matches": skill_priority_matches,
        "skill_path_rows": skill_path_rows,
        "starting_items": starting_items,
        "starting_items_stats": starting_items_stats,
        "core_items": core_items,
        "core_items_stats": core_items_stats,
        "fourth_item_options": fourth_item_options,
        "fifth_item_options": fifth_item_options,
        "sixth_item_options": sixth_item_options

    }

def get_item_text(data, view_type):

    text = ""

    if view_type == 0:

        for item in data:

            item_identifier = f"{item.div.div['style'].split(';')[2].split('/')[-1][:-1]} {item.div.div['style'].split(';')[-4].split(':')[1]}"

            item_data = get_emote("Item", item_identifier)

            text += f"{item_data.split('=')[1]}  {item_data.split('=')[0]}\n"

    else:

        for item in data:

            item_identifier = f"{item.div.div['style'].split(';')[2].split('/')[-1][:-1]} {item.div.div['style'].split(';')[-4].split(':')[1]}"

            item_data = get_emote("Item", item_identifier)

            text += f"{item_data.split('=')[1]}\n"

    return text

def get_detailed_text(build_data):

    main_runes_text = ""
    secondary_runes_text = ""

    for rune_index, rune in enumerate(build_data["runes"]):

        if rune_index == 0:

            main_runes_text += f"{get_emote('Tree', build_data['primary_tree'])}  {build_data['primary_tree']}\n"

            main_runes_text += f"{get_emote('Keystone', rune.img['alt'][13:])}  {rune.img['alt'][13:]}\n"

        elif rune_index in range(1, 4):

            main_runes_text += f"{get_emote('Rune', rune.img['alt'][9:])}  {rune.img['alt'][9:]}\n"

        if rune_index == 4:

            secondary_runes_text += f"{get_emote('Tree', build_data['secondary_tree'])}  {build_data['secondary_tree']}\n"

        if rune_index in range(4, 6):

            secondary_runes_text += f"{get_emote('Rune', rune.img['alt'][9:])}  {rune.img['alt'][9:]}\n"

    shards_text = ""

    for shard in build_data["shards"]:

        emote_mapping = get_emote('Shard', shard.img['alt'][4:][:-6])
        
        if emote_mapping == "Not Found=:x:":

            shards_text += f"{emote_mapping.split("=")[1]}  {shard.img['alt'][4:][:-6]}\n"
            
        else: 
            
            shards_text += f"{emote_mapping}  {shard.img['alt'][4:][:-6]}\n"

    return main_runes_text, secondary_runes_text, shards_text

def get_simple_text(build_data):

    main_runes_text = ""
    secondary_runes_text = ""

    for rune_index, rune in enumerate(build_data["runes"]):

        if rune_index == 0:

            main_runes_text += f"{get_emote('Tree', build_data['primary_tree'])}\n"

            main_runes_text += f"{get_emote('Keystone', rune.img['alt'][13:])}\n"

        elif rune_index in range(1, 4):

            main_runes_text += f"{get_emote('Rune', rune.img['alt'][9:])}\n"

        if rune_index == 4:

            secondary_runes_text += f"{get_emote('Tree', build_data['secondary_tree'])}\n"

        if rune_index in range(4, 6):

            secondary_runes_text += f"{get_emote('Rune', rune.img['alt'][9:])}\n"

    shards_text = ""

    for shard in build_data["shards"]:

        shards_text += f"{get_emote('Shard', shard.img['alt'][4:][:-6])}\n"

    return main_runes_text, secondary_runes_text, shards_text

def get_build_embed(embed, build_data, view_type):
    
    if view_type == 0:

        main_runes_text, secondary_runes_text, shards_text = get_detailed_text(build_data)

    else:

        main_runes_text, secondary_runes_text, shards_text = get_simple_text(build_data)

    summoner_spell_text = ""

    for summoner_spell in build_data["summoner_spells"]:

        summoner_spell_text += f"{get_emote('Summoner Spell', summoner_spell['alt'].split()[-1])} "

    skill_priority_mapping = {

        "Q": "<:q_:1142021169961259038>",
        "W": "<:w_:1142021171278250064>",
        "E": "<:e_:1142021173253779526>"

    }

    starting_items_text = get_item_text(build_data["starting_items"], view_type)
    core_items_text = get_item_text(build_data["core_items"], view_type)
    fourth_item_options_text = get_item_text(build_data["fourth_item_options"], view_type)
    fifth_item_options_text = get_item_text(build_data["fifth_item_options"], view_type)
    sixth_item_options_text = get_item_text(build_data["sixth_item_options"], view_type)

    embed.add_field(name = f"Runes | {build_data['runes_wr']}{build_data['runes_matches']}", value = "", inline = False)
    embed.add_field(name = "", value = f"{main_runes_text}")
    embed.add_field(name = "", value = f"{secondary_runes_text}")
    embed.add_field(name = "", value = f"{shards_text}")
    embed.add_field(name = f"Summoner Spells | {build_data['summoner_spells_wr']}{build_data['summoner_spells_matches']}", value = f"{summoner_spell_text}")
    
    if build_data['skill_priority'] == []:

        embed.add_field(name = f"Skill Priority | {build_data['skill_priority_wr']} WR ({build_data['skill_priority_matches']})", value = f":x: No 'Skill Priority' data was not found.", inline = False)

    else:
    
        embed.add_field(name = f"Skill Priority | {build_data['skill_priority_wr']} WR ({build_data['skill_priority_matches']})", value = f"{skill_priority_mapping[build_data['skill_priority'][0].text]} > {skill_priority_mapping[build_data['skill_priority'][1].text]} > {skill_priority_mapping[build_data['skill_priority'][2].text]}", inline = False)
    
    embed.add_field(name = "Skill Path", value = "", inline = False)

    if build_data["skill_path_rows"] == []:

        embed.add_field(name = f"", value = f":x: No 'Skill Path data was found.", inline = False)

    else:

        embed.add_field(name = "", value = "<:1_:1142013758198251528><:2_:1142014838734856276><:3_:1142014837010993172><:4_:1142014822335139893><:5_:1142014801162281001><:6_:1142014789279809559><:7_:1142014755389845575><:8_:1142014739065618462><:9_:1142015195632386109><:10:1142015179765321781><:11:1142015164749729823><:12:1142015156587614259><:13:1142015154989580311><:14:1142015150661062698><:15:1142015148056387634><:16:1142015131912503358><:17:1142015121154121779><:18:1142015119560282192>", inline = False)

    skill_path_grid = ""

    for row_index, row in enumerate(build_data["skill_path_rows"]):

        for div in row:

            skill_path_grid = edit_skill_path_grid(div, skill_path_grid, row_index)

        skill_path_grid += "\n"
        embed.add_field(name = "", value = f"{skill_path_grid}", inline = False)
        skill_path_grid = ""

    embed.add_field(name = f"Starting Items | {build_data['starting_items_stats']}", value = f"{starting_items_text}", inline = False)
    embed.add_field(name = f"Core Items | {build_data['core_items_stats']}", value = f"{core_items_text}", inline = False)
    embed.add_field(name = f"Fourth Item Options", value = f"{fourth_item_options_text}")
    embed.add_field(name = f"Fifth Item Options", value = f"{fifth_item_options_text}")
    embed.add_field(name = f"Sixth Item Options", value = f"{sixth_item_options_text}")

    return embed

def get_profile_embed(soup):

    try:
        summoner_name = soup.find("div","summoner-name").span.text
    except:
        return embed_error("Summoner name was not found")

    user_img = soup.find("div","profile-icon-border").find("img")
    user_level = soup.find("div","level-header").text

    rank = soup.find("span", "unranked").text
    lp = ""

    if rank  == "":

        rank = soup.find("div", "rank-text").span.text
        lp = soup.find("div", "rank-text").find_all("span")[1].text

    user_winrate = soup.find("div", class_="rank-wins").find_all("span")[1].text if soup.find("div", class_="rank-wins") else "* Ranked winrate could not be found"
    user_win_loss = soup.find("div", class_="rank-wins").find_all("span")[0].text if soup.find("div", class_="rank-wins") else "* Win/Loss information could not be found"
    champions_name = [champion.text for champion in soup.find_all("div", class_="champion-name")] if soup.find_all("div", class_="champion-name") else "No recent available champion information found"
    champions_kda = [kda.text for kda in soup.find_all("div", class_="kda-ratio")] if soup.find_all("div", class_="kda-ratio") else ""
    champions_wr = [wr.text for wr in soup.find_all("div", class_="win-rate")] if soup.find_all("div", class_="win-rate") else ""

    #Reminder - error checking if ranked-wr is None or champions_name,kda,wr is None then we dont pull
    embed = discord.Embed(title=f"{summoner_name}",color = 0x000000)
    embed.set_thumbnail(url= user_img["src"])
    embed.add_field(name="LVL", value=f"{user_level}")
    embed.add_field(name="Rank", value=f"{rank} {lp}")
    embed.add_field(name="Ranked Winrate", value=f"{user_win_loss}\n{user_winrate}",inline=False)
    champions_data = zip(champions_name, champions_kda, champions_wr)

    if champions_kda == "" and champions_wr == "":
        champions_info = champions_name
        embed.add_field(name="Top Played Champions", value=champions_info)
    else:
        champions_info = "\n".join(f"{name} | {kda} | {wr}" for name, kda, wr in champions_data)
        embed.add_field(name="Top Played Champions", value=champions_info)

    return embed

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

    embed = discord.Embed(title = "EggLol Commands", description = "", color = 0x31ABC4)
    
    embed.add_field(name = "", value = "*[] indicates a required field\n{} indicates an optional field*", inline = False)
    embed.add_field(name = "", value = "**/set_profile** [region] [username] [main_champion]\n> Used to create a profile. The benefits of having a profile is a catered experience by auto-filling your region when searching for statistics and auto-filling your main champion in **/vs**.", inline = False)
    embed.add_field(name = "", value = "**/profile** {username} {region}\n> Used to display your current profile if you pass no arguments (ex. /profile) or search for another user in a particular region (region is required for searching). Returns summoner level, rank, win-rate and more.", inline = False)
    embed.add_field(name = "", value = "**/delete_profile** \n> As the name implies, used to delete your profile if you have one.", inline = False)
    embed.add_field(name = "", value = "**/set_preference** [preference]\n> Used to change whether or not you would like to see text beside runes and items. Turn text off if you are a veteran player and know what the runes and items look like to have a cleaner design.", inline = False)
    embed.add_field(name = "", value = "**/overview** [champion_name] {role} {rank} {queue_type} {region}\n> Used to find general statistical data for a champion such as win-rate, ban-rate, matches played and more.", inline = False)
    embed.add_field(name = "", value = "**/build** [champion_name] {role} {rank} {queue_type} {region}\n> Used to find WR, runes, skill priority an build data for a champion.", inline = False)
    embed.add_field(name = "", value = "**/vs** [first_champion] {second_champion} {role} {rank} {queue_type} {region}\n> Used to find win-rate, runes, skill priority an build data for a champion vs. another champion.\n> \n> /vs [first_champion]\n> returns results for your main champion stored in our database vs. [first_champion]\n> \n> /vs [first_champion] {second_champion}\n> returns results for [first_champion] vs. {second_champion}", inline = False)
    embed.add_field(name = "Links", value = "[U.GG](https://u.gg) | [EggLoL Github Repository](https://github.com/alia720/EggLoL)", inline = False)
    #
    await interaction.followup.send(embed = embed)
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

async def set_profile(interaction: discord.Interaction, region: app_commands.Choice[str], username: app_commands.Range[str, 3, 16], main_champion: app_commands.Range[str, 3, 14]):

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

    except AttributeError:

        error_msg += f"* The username **{username}** was not found in the **{region}** region. *Try another region or double-check the username*.\n"

    if is_valid_champion(main_champion) == False:

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

    main_champion_for_ui = get_champion_for_ui(main_champion)
    main_champion_for_db = main_champion_for_ui.replace("'", '"')

    # Checkpoint | main_champion has been character corrected

    uuid = uuid7()
    discord_user_id = interaction.user.id

    initial_query_resp = query_mainpulate_data(f"INSERT INTO discord_user (discord_user_id) VALUES ({discord_user_id});")

    if initial_query_resp == 400:

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

@bot.tree.command(name = "overview", description = "Get an overview of the champion in your specific rank, region and role!")
@app_commands.describe(champion_name = "Champion to get overview for")
@app_commands.choices(
    
    role = [
    
        app_commands.Choice(name = "Top", value = "top"),
        app_commands.Choice(name = "Jungle", value = "jungle"),
        app_commands.Choice(name = "Middle", value = "mid"),
        app_commands.Choice(name = "Bot/ADC", value = "adc"),
        app_commands.Choice(name = "Support", value = "support")

    ],
    rank = [

        app_commands.Choice(name = "Platinum +", value = "platinum_plus"),
        app_commands.Choice(name = "Emerald +", value = "emerald_plus"),
        app_commands.Choice(name = "Diamond +", value = "diamond_plus"),
        app_commands.Choice(name = "Diamond 2 +", value = "diamond_2_plus"),
        app_commands.Choice(name = "Master +", value = "master_plus"),
        app_commands.Choice(name = "All Ranks", value = "overall"),
        app_commands.Choice(name = "Challenger", value = "challenger"),
        app_commands.Choice(name = "Grandmaster", value = "grandmaster"),
        app_commands.Choice(name = "Master", value = "master"),
        app_commands.Choice(name = "Diamond", value = "diamond"),
        app_commands.Choice(name = "Emerald", value = "emerald"),
        app_commands.Choice(name = "Platinum", value = "platinum"),
        app_commands.Choice(name = "Gold", value = "gold"),
        app_commands.Choice(name = "Silver", value = "silver"),
        app_commands.Choice(name = "Bronze", value = "bronze"),
        app_commands.Choice(name = "Iron", value = "iron")

    ],
    queue_type = [

        app_commands.Choice(name = "Ranked Solo/Duo", value = ""),
        app_commands.Choice(name = "ARAM", value = "aram"),
        app_commands.Choice(name = "Ranked Flex", value = "ranked_flex_sr"),
        app_commands.Choice(name = "Normal Blind", value = "normal_blind_5x5"),
        app_commands.Choice(name = "Normal Draft", value = "normal_draft_5x5")

    ],
    region = [

        app_commands.Choice(name = "World", value = "world"),
        app_commands.Choice(name = "NA", value = "na1"),
        app_commands.Choice(name = "EUW", value = "euw1"),
        app_commands.Choice(name = "KR", value = "kr"),
        app_commands.Choice(name = "BR", value = "br1"),
        app_commands.Choice(name = "EUN", value = "eun1"),
        app_commands.Choice(name = "JP", value = "jp1"),
        app_commands.Choice(name = "LAN", value = "la1"),
        app_commands.Choice(name = "LAS", value = "la2"),
        app_commands.Choice(name = "OCE", value = "oc1"),
        app_commands.Choice(name = "RU", value = "ru"),
        app_commands.Choice(name = "TR", value = "tr1"),
        app_commands.Choice(name = "PH", value = "ph1"),
        app_commands.Choice(name = "SG", value = "sg2"),
        app_commands.Choice(name = "TH", value = "th2"),
        app_commands.Choice(name = "TW", value = "tw2"),
        app_commands.Choice(name = "VN", value = "vn2")

    ]
)

async def overview(interaction: discord.Interaction, champion_name: str, role: Optional[app_commands.Choice[str]] = None, rank: Optional[app_commands.Choice[str]] = '{"name": "Emerald +"}',  queue_type: Optional[app_commands.Choice[str]] = '{"name": "Ranked Solo/Duo"}', region: Optional[app_commands.Choice[str]] = '{"name": "World", "value": "World"}'):

    await interaction.response.defer(ephemeral = False)

    url, champion_name_for_ui, rank, queue_type, region, error_msg = create_url(interaction, champion_name, role, rank, queue_type, region)

    if error_msg != "":

        await interaction.followup.send(embed = embed_error(error_msg))
        return

    soup = await aio_get_soup(url)

    if queue_type.name != "ARAM":
        
        role = soup.find("div", "role-value").div.text

    try:

        tier = soup.find("div", "champion-tier").div.text
        win_rate = soup.find("div", "win-rate").div.text
        overall_rank = soup.find("div", "overall-rank").div.text
        pick_rate = soup.find("div", "pick-rate").div.text
        ban_rate = soup.find("div", "ban-rate").div.text
        total_matches = soup.find("div", "matches").div.text
    
    except AttributeError:

        await interaction.followup.send(embed = embed_error(f"* No data was found for {champion_name_for_ui} in the following criteria:\n * {region.name}\n * {queue_type.name}\n * {rank.name}\n * {role}"))
        return

    if queue_type.name != "ARAM":

        embed = discord.Embed(title = f"{champion_name_for_ui} | {role}", description = f"**{queue_type.name}** in **{region.name}**\n{get_emote('Rank', rank.name.split()[0])} {rank.name}", url = url,  color = 0x222247)

    else:
        
        embed = discord.Embed(title = f"{champion_name_for_ui}", description = f"**{queue_type.name}** in **{region.name}**", url = url,  color = 0x222247)

    champion_icon_dir = get_emote("Champion", champion_name_for_ui)
    champion_icon = discord.File(champion_icon_dir, filename = f"{champion_icon_dir.split('/')[-1]}")
    embed.set_thumbnail(url = f"attachment://{champion_icon_dir.split('/')[-1]}")

    embed.add_field(name = "Tier", value =  f"{tier}")
    embed.add_field(name = "Win Rate", value =  f"{win_rate}")
    embed.add_field(name = "Position", value =  f"{overall_rank}")
    embed.add_field(name = "Pick Rate", value =  f"{pick_rate}")
    embed.add_field(name = "Ban Rate", value =  f"{ban_rate}")
    embed.add_field(name = "Matches", value =  f"{total_matches}")

    embed.set_footer(text = f"Powered by U.GG", icon_url = "https://pbs.twimg.com/profile_images/1146442344662798336/X1Daf_aS_400x400.png")

    await interaction.followup.send(embed = embed, file = champion_icon)
    return

@bot.tree.command(name = "build", description = "Get the complete build for the champion including the runes, summoner spells, items and more.")
@app_commands.describe(champion_name = "Champion to get build for")
@app_commands.choices(

    role = [
    
        app_commands.Choice(name = "Top", value = "top"),
        app_commands.Choice(name = "Jungle", value = "jungle"),
        app_commands.Choice(name = "Middle", value = "mid"),
        app_commands.Choice(name = "Bot/ADC", value = "adc"),
        app_commands.Choice(name = "Support", value = "support")

    ],
    rank = [

        app_commands.Choice(name = "Platinum +", value = "platinum_plus"),
        app_commands.Choice(name = "Emerald +", value = "emerald_plus"),
        app_commands.Choice(name = "Diamond +", value = "diamond_plus"),
        app_commands.Choice(name = "Diamond 2 +", value = "diamond_2_plus"),
        app_commands.Choice(name = "Master +", value = "master_plus"),
        app_commands.Choice(name = "All Ranks", value = "overall"),
        app_commands.Choice(name = "Challenger", value = "challenger"),
        app_commands.Choice(name = "Grandmaster", value = "grandmaster"),
        app_commands.Choice(name = "Master", value = "master"),
        app_commands.Choice(name = "Diamond", value = "diamond"),
        app_commands.Choice(name = "Emerald", value = "emerald"),
        app_commands.Choice(name = "Platinum", value = "platinum"),
        app_commands.Choice(name = "Gold", value = "gold"),
        app_commands.Choice(name = "Silver", value = "silver"),
        app_commands.Choice(name = "Bronze", value = "bronze"),
        app_commands.Choice(name = "Iron", value = "iron")

    ],
    queue_type = [

        app_commands.Choice(name = "Ranked Solo/Duo", value = ""),
        app_commands.Choice(name = "ARAM", value = "aram"),
        app_commands.Choice(name = "Ranked Flex", value = "ranked_flex_sr"),
        app_commands.Choice(name = "Normal Blind", value = "normal_blind_5x5"),
        app_commands.Choice(name = "Normal Draft", value = "normal_draft_5x5")

    ],
    region = [

        app_commands.Choice(name = "World", value = "world"),
        app_commands.Choice(name = "NA", value = "na1"),
        app_commands.Choice(name = "EUW", value = "euw1"),
        app_commands.Choice(name = "KR", value = "kr"),
        app_commands.Choice(name = "BR", value = "br1"),
        app_commands.Choice(name = "EUN", value = "eun1"),
        app_commands.Choice(name = "JP", value = "jp1"),
        app_commands.Choice(name = "LAN", value = "la1"),
        app_commands.Choice(name = "LAS", value = "la2"),
        app_commands.Choice(name = "OCE", value = "oc1"),
        app_commands.Choice(name = "RU", value = "ru"),
        app_commands.Choice(name = "TR", value = "tr1"),
        app_commands.Choice(name = "PH", value = "ph1"),
        app_commands.Choice(name = "SG", value = "sg2"),
        app_commands.Choice(name = "TH", value = "th2"),
        app_commands.Choice(name = "TW", value = "tw2"),
        app_commands.Choice(name = "VN", value = "vn2")

    ]
)

async def build(interaction: discord.Interaction, champion_name: str, role: Optional[app_commands.Choice[str]] = None, rank: Optional[app_commands.Choice[str]] = '{"name": "Emerald +"}',  queue_type: Optional[app_commands.Choice[str]] = '{"name": "Ranked Solo/Duo"}', region: Optional[app_commands.Choice[str]] = '{"name": "World", "value": "World"}'):

    await interaction.response.defer(ephemeral = False)

    url, champion_name_for_ui, rank, queue_type, region, error_msg = create_url(interaction, champion_name, role, rank, queue_type, region)

    if error_msg != "":

        await interaction.followup.send(embed = embed_error(error_msg))
        return

    soup = await aio_get_soup(url)

    build_data = get_build_data(soup, champion_name_for_ui)

    if queue_type.name != "ARAM":
        
        role = soup.find("div", "role-value").div.text

    if "Error" in build_data:

        await interaction.followup.send(embed = embed_error(f"{build_data['Error'][:-1]} in the following criteria:\n * {region.name}\n * {queue_type.name}\n * {rank.name}\n * {role}"))
        return

    if queue_type.name != "ARAM":

        if queue_type.name == "Ranked Solo/Duo" or queue_type.name == "Ranked Flex":

            embed = discord.Embed(title = f"{champion_name_for_ui} | {role}", description = f"**{queue_type.name}** in **{region.name}**\n{get_emote('Rank', rank.name.split()[0])} {rank.name}", url = url,  color = 0x222247)

        else:

            embed = discord.Embed(title = f"{champion_name_for_ui} | {role}", description = f"**{queue_type.name}** in **{region.name}**", url = url,  color = 0x222247)

    else:
        
        embed = discord.Embed(title = f"{champion_name_for_ui}", description = f"**{queue_type.name}** in **{region.name}**", url = url,  color = 0x222247)

    champion_icon_dir = get_emote("Champion", champion_name_for_ui)
    champion_icon = discord.File(champion_icon_dir, filename = f"{champion_icon_dir.split('/')[-1]}")
    embed.set_thumbnail(url = f"attachment://{champion_icon_dir.split('/')[-1]}")

    current_preference_resp = query_get_data(f"SELECT build_format_preference FROM discord_user WHERE discord_user_id = {interaction.user.id};")

    if current_preference_resp == 400 or current_preference_resp == None:

        # Sets to default preference if error or they don't have a profile
        current_preference = 0

    else:

        current_preference = current_preference_resp[0]

        # Sets to default preference if profile exists but they have not set preference
        if current_preference == None:

            current_preference = 0

    build_embed = get_build_embed(embed, build_data, current_preference)

    embed.set_footer(text = f"Powered by U.GG", icon_url = "https://pbs.twimg.com/profile_images/1146442344662798336/X1Daf_aS_400x400.png")

    await interaction.followup.send(embed = build_embed, file = champion_icon)
    return

@bot.tree.command(name = "vs", description = "Get the complete build and WR for your champion vs. another champion!")
@app_commands.describe(first_champion = "main_champion vs. first_champion OR first_champion vs. second_champion", second_champion = "first_champion vs. second_champion")
@app_commands.choices(
    
    role = [
    
        app_commands.Choice(name = "Top", value = "top"),
        app_commands.Choice(name = "Jungle", value = "jungle"),
        app_commands.Choice(name = "Middle", value = "mid"),
        app_commands.Choice(name = "Bot/ADC", value = "adc"),
        app_commands.Choice(name = "Support", value = "support")

    ],
    rank = [

        app_commands.Choice(name = "Platinum +", value = "platinum_plus"),
        app_commands.Choice(name = "Emerald +", value = "emerald_plus"),
        app_commands.Choice(name = "Diamond +", value = "diamond_plus"),
        app_commands.Choice(name = "Diamond 2 +", value = "diamond_2_plus"),
        app_commands.Choice(name = "Master +", value = "master_plus"),
        app_commands.Choice(name = "All Ranks", value = "overall"),
        app_commands.Choice(name = "Challenger", value = "challenger"),
        app_commands.Choice(name = "Grandmaster", value = "grandmaster"),
        app_commands.Choice(name = "Master", value = "master"),
        app_commands.Choice(name = "Diamond", value = "diamond"),
        app_commands.Choice(name = "Emerald", value = "emerald"),
        app_commands.Choice(name = "Platinum", value = "platinum"),
        app_commands.Choice(name = "Gold", value = "gold"),
        app_commands.Choice(name = "Silver", value = "silver"),
        app_commands.Choice(name = "Bronze", value = "bronze"),
        app_commands.Choice(name = "Iron", value = "iron")

    ],
    queue_type = [

        app_commands.Choice(name = "Ranked Solo/Duo", value = ""),
        app_commands.Choice(name = "Ranked Flex", value = "ranked_flex_sr"),

    ],
    region = [

        app_commands.Choice(name = "World", value = "world"),
        app_commands.Choice(name = "NA", value = "na1"),
        app_commands.Choice(name = "EUW", value = "euw1"),
        app_commands.Choice(name = "KR", value = "kr"),
        app_commands.Choice(name = "BR", value = "br1"),
        app_commands.Choice(name = "EUN", value = "eun1"),
        app_commands.Choice(name = "JP", value = "jp1"),
        app_commands.Choice(name = "LAN", value = "la1"),
        app_commands.Choice(name = "LAS", value = "la2"),
        app_commands.Choice(name = "OCE", value = "oc1"),
        app_commands.Choice(name = "RU", value = "ru"),
        app_commands.Choice(name = "TR", value = "tr1"),
        app_commands.Choice(name = "PH", value = "ph1"),
        app_commands.Choice(name = "SG", value = "sg2"),
        app_commands.Choice(name = "TH", value = "th2"),
        app_commands.Choice(name = "TW", value = "tw2"),
        app_commands.Choice(name = "VN", value = "vn2")

    ]
)
async def vs(interaction: discord.Interaction, first_champion: str, second_champion: Optional[str] = None, role: Optional[app_commands.Choice[str]] = None, rank: Optional[app_commands.Choice[str]] = '{"name": "Emerald +"}',  queue_type: Optional[app_commands.Choice[str]] = '{"name": "Ranked Solo/Duo"}', region: Optional[app_commands.Choice[str]] = '{"name": "World", "value": "World"}'):

    await interaction.response.defer(ephemeral = False)

    if second_champion == None:

        if is_valid_champion(first_champion) == False:

            await interaction.followup.send(embed = embed_error(f"* **{first_champion}** is not a champion in League of Legends.\n"))
            return

        my_champion = query_get_data(f"SELECT main_champion FROM discord_user JOIN lol_profile USING (profile_uuid) WHERE discord_user_id = {interaction.user.id};")

        if my_champion == None:

            await interaction.followup.send(embed = embed_error(f"* It appears that you have not set up your profile! If you would like to, use /set_profile. If you would like to use this function without setting up your profile, specify **second_champion** when calling this function."))
            return
        
        my_champion = my_champion[0]

        opp = first_champion
        
    else:

        error_msg = ""

        if is_valid_champion(first_champion) == False:

            error_msg += f"* **{first_champion}** is not a champion in League of Legends.\n"

        if is_valid_champion(second_champion) == False:

            error_msg += f"* **{second_champion}** is not a champion in League of Legends.\n"

        if error_msg != "":

            await interaction.followup.send(embed = embed_error(error_msg))
            return
        
        my_champion = first_champion
        opp = second_champion

    # Checkpoint | 'my_champion' and 'opp' have been verified and assigned

    url, my_champion_for_ui, rank, queue_type, region, error_msg = create_url(interaction, my_champion, role, rank, queue_type, region)

    url += f"opp={get_champion_for_url(opp)}"

    soup = await aio_get_soup(url)

    build_data = get_build_data(soup, my_champion_for_ui)

    role = soup.find("div", "role-value").div.text

    if "Error" in build_data:

        await interaction.followup.send(embed = embed_error(f"{build_data['Error'][:-1]} vs. {get_champion_for_ui(opp)} in the following criteria:\n * {region.name}\n * {queue_type.name}\n * {rank.name}\n * {role}"))
        return

    embed = discord.Embed(title = f"{my_champion_for_ui} vs. {get_champion_for_ui(opp)} | {role}", description = f"**{queue_type.name}** in **{region.name}**\n{get_emote('Rank', rank.name.split()[0])} {rank.name}", url = url, color = 0xD13441)

    champion_icon_dir = get_emote("Champion", my_champion_for_ui)
    champion_icon = discord.File(champion_icon_dir, filename = f"{champion_icon_dir.split('/')[-1]}")
    embed.set_thumbnail(url = f"attachment://{champion_icon_dir.split('/')[-1]}")

    embed.add_field(name = "WR", value = f"{soup.find('div', 'champion-ranking-stats-normal').find('div', 'win-rate').div.text}")
    embed.add_field(name = "Matches", value = f"{soup.find('div', 'champion-ranking-stats-normal').find('div', 'matches-oppid').div.text}")
    embed.add_field(name = "", value = "", inline = False)

    current_preference_resp = query_get_data(f"SELECT build_format_preference FROM discord_user WHERE discord_user_id = {interaction.user.id};")

    if current_preference_resp == 400 or current_preference_resp == None:

        # Sets to default preference if error or they don't have a profile
        current_preference = 0

    else:

        current_preference = current_preference_resp[0]

        # Sets to default preference if profile exists but they have not set preference
        if current_preference == None:

            current_preference = 0

    build_embed = get_build_embed(embed, build_data, current_preference)

    embed.set_footer(text = f"Powered by U.GG", icon_url = "https://pbs.twimg.com/profile_images/1146442344662798336/X1Daf_aS_400x400.png")

    await interaction.followup.send(embed = build_embed, file = champion_icon)
    return

@bot.tree.command(name = "profile", description = "Retrieve your profile data from our database or search for someone else's!")
@app_commands.choices(region = [
    app_commands.Choice(name = "NA", value = "na1"),
    app_commands.Choice(name = "EUW", value = "euw1"),
    app_commands.Choice(name = "KR", value = "kr"),
    app_commands.Choice(name = "BR", value = "br1"),
    app_commands.Choice(name = "EUN", value = "eun1"),
    app_commands.Choice(name = "JP", value = "jp1"),
    app_commands.Choice(name = "LAN", value = "la1"),
    app_commands.Choice(name = "LAS", value = "la2"),
    app_commands.Choice(name = "OCE", value = "oc1"),
    app_commands.Choice(name = "RU", value = "ru"),
    app_commands.Choice(name = "TR", value = "tr1"),
    app_commands.Choice(name = "PH", value = "ph1"),
    app_commands.Choice(name = "SG", value = "sg2"),
    app_commands.Choice(name = "TH", value = "th2"),
    app_commands.Choice(name = "TW", value = "tw2"),
    app_commands.Choice(name = "VN", value = "vn2")
    ])
async def profile(interaction: discord.Interaction, username: Optional[str] = None, region: Optional[app_commands.Choice[str]] = None):

    await interaction.response.defer(ephemeral=False)

    # Retrieve user's profile from the database
    discord_profile = interaction.user.id
    
    if username == None and region == None:

        user_profile = query_get_data(f"SELECT region, username, rank FROM discord_user JOIN lol_profile USING (profile_uuid) WHERE discord_user_id = {discord_profile}")
            
        if user_profile == 400:

            await interaction.followup.send(embed = embed_error(f"* Something went wrong while fetching your profile. Try again later."))
            return
        
        if user_profile == None:
            
            await interaction.followup.send(embed = embed_error(f"* You do not have a profile set. Use /setprofile to create one!"))
            return

        
        user_url = f"https://u.gg/lol/profile/{get_region_for_url(user_profile[0])}/{user_profile[1]}/overview"
        soup = await aio_get_soup(user_url)

        embed = get_profile_embed(soup)
        
        await interaction.followup.send(embed=embed, ephemeral=False)
        return
    
    elif username == None and region != None:

        embed = embed_error("You did not specify a Summoner name")

        await interaction.followup.send(embed = embed, ephemeral = False)
        return
    
    elif username != None and region == None:

        embed = embed_error("You did not specify a Region")

        await interaction.followup.send(embed=embed, ephemeral=False)
        return

    else:

        user_url = f"https://u.gg/lol/profile/{region.value}/{username}/overview"
        soup = await aio_get_soup(user_url)

        embed = get_profile_embed(soup)
        
        await interaction.followup.send(embed=embed, ephemeral=False)
        return

@bot.tree.command(name = "delete_profile", description = "Delete your profile.")
async def delete_profile(interaction: discord.Interaction):

    await interaction.response.defer(ephemeral=False)

    discord_profile = interaction.user.id

    discord_user = query_get_data(f"SELECT discord_user_id, profile_uuid FROM discord_user WHERE discord_user_id = {discord_profile}")

    if discord_user:

        profile_uuid = discord_user[1]

        status_code_discord_user = query_mainpulate_data(f"DELETE FROM discord_user WHERE discord_user_id = {discord_profile};")
        status_code_lol_profile = query_mainpulate_data(f"DELETE FROM lol_profile WHERE profile_uuid = '{profile_uuid}';")
        
        if status_code_discord_user == 200 and status_code_lol_profile == 200:
            embed = discord.Embed(description="Profile deleted successfully.", color=discord.Color.green())
        else:
            embed = discord.Embed(description="Failed to delete profile.", color=discord.Color.red())
    else:
        embed = discord.Embed(description="Profile not found.", color=discord.Color.orange())

    await interaction.followup.send(embed=embed, ephemeral=False)
    return

@bot.tree.command(name = "set_preference", description = "Choose whether or not you would like to see text beside runes and items to better identify them.")
@app_commands.describe(preference = "Show Text (Set by Default) | Do Not Show Text (For Experienced Players)")
@app_commands.choices(preference = [

    app_commands.Choice(name = "Show Text", value = 0),
    app_commands.Choice(name = "Do Not Show Text", value = 1)

])
async def set_preference(interaction: discord.Integration, preference: app_commands.Choice[int]):

    await interaction.response.defer(ephemeral=False)

    user_choice = preference.value

    user_id = interaction.user.id

    current_preference_resp = query_get_data(f"SELECT build_format_preference FROM discord_user WHERE discord_user_id = {user_id};")

    if current_preference_resp == 400:

        await interaction.followup.send(embed = embed_error("* Something went wrong when trying to update your preference. Please try again later."))
        return
    
    elif current_preference_resp == None:
    
        await interaction.followup.send(embed = embed_error("* It looks like you currently do not have a profile. Use `/set_profile` to do so."))
        return
    
    else:

        current_preference = current_preference_resp[0]

    if current_preference == None and user_choice == 0:

        await interaction.followup.send(embed = embed_error("* The default preference is set to 'Show Text'."))
        return

    if current_preference == user_choice:

        await interaction.followup.send(embed = embed_error(f"* Your current preference is already set to '{preference.name}'."))
        return
    
    if query_mainpulate_data(f"UPDATE discord_user SET build_format_preference = {user_choice} WHERE discord_user_id = {user_id};") == 400:

        await interaction.followup.send(embed = embed_error(f"* Something went wrong when trying to update your preference. Please try again later."))
        return
    
    else: 

        embed = discord.Embed(title = "Success", description = f"Your preference has succesfully been updated to '{preference.name}'.", color = 0x00AA00)

        await interaction.followup.send(embed = embed, ephemeral = False)
        return

bot.run(TOKEN)