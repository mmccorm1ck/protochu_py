import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import psycopg
from psycopg_pool import AsyncConnectionPool
import contextlib
import os
import sys
from typing import cast

load_dotenv()
token: str | None = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

conn_string: str = f"host={os.getenv('POSTGRES_ADDR')} port={os.getenv('POSTGRES_PORT')} dbname=protochu_db user={os.getenv('POSTGRES_USER')} password={os.getenv('POSTGRES_PSWD')}"
pool = AsyncConnectionPool(conninfo=conn_string, open=False, max_size=20, max_idle=60)

@contextlib.asynccontextmanager
async def get_cursor():
    async with pool.connection() as conn, conn.transaction(), conn.cursor() as cur:
        yield conn, cur

@bot.event
async def on_ready() -> None:
    try:
        await pool.open(wait=True)
        async with get_cursor() as (_, cur):
            print("Check servers table")
            await cur.execute("""CREATE TABLE IF NOT EXISTS servers (
                id bigint PRIMARY KEY,
                name varchar(255),
                curr_tournament int,
                link_channels int[] DEFAULT array[]::int[],
                result_channel int
            );
            """)
            print("Check players table")
            await cur.execute("""CREATE TABLE IF NOT EXISTS players (
                id bigint PRIMARY KEY,
                name varchar(255),
                ps_names varchar(255)[] DEFAULT array[]::varchar[]
            );
            """)
            print("Check tournaments table")
            await cur.execute("""CREATE TABLE IF NOT EXISTS tournaments (
                id int PRIMARY KEY,
                name varchar(255),
                server_id bigint REFERENCES servers,
                battle_format varchar(255),
                tournament_format text,
                no_of_players int,
                player_ids bigint[] DEFAULT array[]::bigint[],
                start_date date,
                current_week int,
                no_of_weeks int
            );
            """)        
            print("Check weeks table")
            await cur.execute("""CREATE TABLE IF NOT EXISTS weeks (
                id int PRIMARY KEY,
                week_no int,
                tournament_id int REFERENCES tournaments,
                no_of_matches int
            );
            """)
            print("Check matches table")
            await cur.execute("""CREATE TABLE IF NOT EXISTS matches (
                id int PRIMARY KEY,
                week_id int REFERENCES weeks,
                player1_id bigint,
                player2_id bigint,
                winner bigint,
                score int
            );
            """)
            print("Check games table")
            await cur.execute("""CREATE TABLE IF NOT EXISTS games (
                id int PRIMARY KEY,
                match_id int REFERENCES weeks,
                player1_id bigint,
                player2_id bigint,
                winner bigint,
                replay_link varchar(255),
                result text
            );
            """)
            print("Table checks complete")
    except psycopg.Error as e:
        print(e)
        sys.exit(1)
    else:
        if bot.user:
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
async def on_reaction_add(reaction: discord.Reaction, user: discord.User) -> None:
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
async def analyse(ctx: commands.Context[commands.Bot], *, msg: str) -> None:
    if not "https://replay.pokemonshowdown.com/" in msg:
        await ctx.message.reply("Invalid replay link")
        return
    #run analysis

@bot.command()
async def add_username(ctx: commands.Context[commands.Bot], *, msg: str) -> None:
    async with get_cursor() as (_, cur):
        try:
            await cur.execute("""
                INSERT INTO players (id, name, ps_names)
                VALUES (%s, %s, DEFAULT)
                ON CONFLICT (id) DO NOTHING;
                """,
                (ctx.author.id, ctx.author.name))
            await cur.execute("""
                SELECT ps_names FROM players WHERE id = %s;
                """,
                (ctx.author.id,))
            current_ps_names: list[str] = cast(tuple[list[str]], await cur.fetchone())[0]
            if msg in current_ps_names:
                print("username already assigned")
                current_ps_names_str: str = '\n'.join(current_ps_names)
                await ctx.send(f"{msg} is already set as a showdown username for {ctx.author.mention}. Current usernames are:\n{current_ps_names_str}")
                return
            current_ps_names.append(msg)
            await cur.execute("""
                UPDATE players
                SET ps_names = %s
                WHERE id = %s
                """,
                (current_ps_names, ctx.author.id))
            current_ps_names_str: str = '\n'.join(current_ps_names)
            await ctx.send(f"{msg} has been added as a showdown username for {ctx.author.mention}. Current usernames are:\n{current_ps_names_str}")
        except psycopg.Error as e:
            print(e)


@bot.command()
async def remove_username(ctx: commands.Context[commands.Bot], *, msg: str) -> None:
    async with get_cursor() as (_, cur):
        try:
            await cur.execute("""
                INSERT INTO players (id, name, ps_names)
                VALUES (%s, %s, DEFAULT)
                ON CONFLICT (id) DO NOTHING;
                """,
                (ctx.author.id, ctx.author.name))
            await cur.execute("""
                SELECT ps_names FROM players WHERE id = %s;
                """,
                (ctx.author.id,))
            current_ps_names: list[str] = cast(tuple[list[str]], await cur.fetchone())[0]
            if len(current_ps_names) == 0:
                await ctx.send(f"No showdown usernames have been assigned to {ctx.author.mention}")
                return
            if msg not in current_ps_names:
                current_ps_names_str: str = '\n'.join(current_ps_names)
                await ctx.send(f"{msg} is not set as a showdown username for {ctx.author.mention}. Current usernames are:\n{current_ps_names_str}")
                return
            current_ps_names.remove(msg)
            await cur.execute("""
                UPDATE players
                SET ps_names = %s
                WHERE id = %s
                """,
                (current_ps_names, ctx.author.id))
            current_ps_names_str: str
            if len(current_ps_names) == 0:
                current_ps_names_str = "All usernames have been removed"
            else:
                current_ps_names_str = 'Current usernames are:\n' + '\n'.join(current_ps_names)
            await ctx.send(f"{msg} has been removed as a showdown username for {ctx.author.mention}. {current_ps_names_str}")
        except psycopg.Error as e:
            print(e)

@bot.command()
async def add_links(ctx: commands.Context[commands.Bot]) -> None:
    #add channel to database
    await ctx.send("Listening in channel for battle links")

@bot.command()
async def remove_links(ctx: commands.Context[commands.Bot]) -> None:
    #remove channel from database
    await ctx.send("Stopped listening in channel for battle links")

@bot.command()
async def add_results(ctx: commands.Context[commands.Bot]) -> None:
    #add channel to database
    await ctx.send("Channel set as output for battle results")

if token:
    bot.run(token=token, log_handler=handler, log_level=logging.DEBUG)