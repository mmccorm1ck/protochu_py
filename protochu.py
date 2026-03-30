import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os

load_dotenv()
token: str = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready() -> None:
    print(f"{bot.user.name}, I choose you!")

@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author == bot.user:
        return
    if "https://play.pokemonshowdown.com/battle" in message.content:
        await message.add_reaction("🔍")
        #watch battle
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction: discord.Reaction, user) -> None:
    if reaction.message.author != bot.user:
        return
    if reaction.emoji == "🔄":
        await reaction.message.channel.send("Re-running replay analysis")
        #re-run replay analysis
        text: str = reaction.message.content + " - edited"
        await reaction.message.edit(content=text)
        return
    if reaction.emoji == "❌":
        #remove game data from database
        await reaction.message.delete()
        await reaction.message.channel.send("Removed game from history")
        return

@bot.command()
async def analyse(ctx: commands.Context, *, msg: str) -> None:
    if not "https://replay.pokemonshowdown.com/" in msg:
        await ctx.message.reply("Invalid replay link")
        return
    #run analysis

@bot.command()
async def add_username(ctx: commands.Context, *, msg: str) -> None:
    split_msg: list[str] = msg.split(' ')
    for username in split_msg:
        #add username to database
        await ctx.send(f"{username} has been added as a showdown username for {ctx.author.mention}")

@bot.command()
async def remove_username(ctx: commands.Context, *, msg: str) -> None:
    split_msg: list[str] = msg.split(' ')
    for username in split_msg:
        #remove username from database
        await ctx.send(f"{username} has been removed as a showdown username for {ctx.author.mention}")

@bot.command()
async def add_links(ctx: commands.Context) -> None:
    #add channel to database
    await ctx.send("Listening in channel for battle links")

@bot.command()
async def remove_links(ctx: commands.Context) -> None:
    #remove channel from database
    await ctx.send("Stopped listening in channel for battle links")

@bot.command()
async def add_results(ctx: commands.Context) -> None:
    #add channel to database
    await ctx.send("Channel set as output for battle results")

bot.run(token=token, log_handler=handler, log_level=logging.DEBUG)