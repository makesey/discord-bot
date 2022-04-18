import asyncio
from collections import deque
import logging
from random import shuffle

import discord
from discord.ext import commands, tasks
from youtube_dl import YoutubeDL


# Logger
logger = logging.getLogger('discord.bot').getChild(__name__)
logger.setLevel(logging.INFO)
ydl_logger = logger.getChild('ydl')

YDL_OPTS = {
    'format': 'bestaudio[acodec=opus]/bestaudio/best',
    'default_search': 'ytsearch',
    'logger': ydl_logger
}

YDL = YoutubeDL(YDL_OPTS)

# tasks event loop
loop = asyncio.get_event_loop()

# Checks
async def bot_voice_connected(ctx):
    success = False
    if ctx.voice_client:
        success = ctx.voice_client.is_connected()

    if not success:
        logger.info('Check failed: bot_voice_connected')
        await ctx.send('Bot is not connected to a voice channel')

    return success

async def user_voice_connected(ctx):
    success = False
    if ctx.author.voice:
        success = True

    if not success:
        logger.info('Check failed: user_voice_connected')
        await ctx.send('You have to be connected to a voice channel')
    
    return success

async def playing(ctx):
    success = False
    if ctx.voice_client:
        if ctx.voice_client.is_playing():
            success = True

    if not success:
        logger.info('Check failed: playing')
        await ctx.send('Currently not playing anything')

    return success

async def paused(ctx):
    success = False
    if ctx.voice_client:
        if ctx.voice_client.is_paused():
            success = True

    if not success:
        logger.info('Check failed: voice')
        await ctx.send('Currently not paused')

    return success


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = deque()
        self.vc = None

    def cog_unload(self):
        logger.info('Unload cog')
        self.auto_disconnect.cancel()
        self.auto_disconnect.change_interval(seconds=0.0)
        self.auto_disconnect.start()

    async def get_info(self, search):
        logger.info(f'Getting video info for {search}')
        # extract_info() would block the main code, consequently blocking the discord gateway heartbeat
        # so we do it in an extra thread
        ydl_info = await asyncio.to_thread(YDL.extract_info, search, download=False)

        # get first item from playlist
        if ydl_info['_type'] == 'playlist':
            vid = ydl_info['entries'][0]
        else:
            vid = ydl_info

        # log video info
        logger.info('youtube-dl info:')
        logger.info(f"\next: {vid['ext']}\nfilesize: {vid['filesize']}\ntbr: {vid['tbr']}\nacodec: {vid['acodec']}\nasr: {vid['asr']}\nabr: {vid['abr']}")

        return vid

    def create_source(self, vid):
        # create audio source
        logger.info('Creating audio source')
        if vid['acodec'] == 'opus':
            source = discord.FFmpegOpusAudio(vid['url'], codec='copy')
        else:
            source = discord.FFmpegOpusAudio(vid['url'])

        return source

    def play_song(self, _):
        # check if we are connected
        # "after" call triggers after auto-disconnect already disconnected the bot
        if not self.vc.is_connected():
            return

        if len(self.song_queue) == 0:
            # start auto disconnect task
            logger.info('Start auto_disconnect timer')
            self.auto_disconnect.start()
            return

        # cancel auto_disconnect if running
        self.auto_disconnect.cancel()

        # Get next song
        vid = self.song_queue.popleft()
        logger.info(f'Getting "{vid["title"]}" from queue')

        source = self.create_source(vid)

        logger.info(f"Playing song {vid['title']}")
        self.vc.play(source, after=self.play_song)
        self.current_song = vid


    # Tasks
    @tasks.loop(minutes=5.0, count=2, loop=loop)
    async def auto_disconnect(self):
        # only run on second loop
        if self.auto_disconnect.current_loop > 0:
            logger.info('Auto-Disconnect')
            self.queue = deque()
            if self.vc:
                await self.vc.disconnect()

    # Commands
    @commands.command(brief='Connect to a voice channel')
    @commands.check(user_voice_connected)
    async def connect(self, ctx):
        voice_channel = ctx.author.voice.channel
        logger.info(f'Connecting to voice channel: "{voice_channel}" id={voice_channel.id}')
        self.vc = await voice_channel.connect()

        # react if called directly
        if ctx.invoked_with == self.connect.name:
            await ctx.message.add_reaction('✅')

    @commands.command(brief='Disconnect from a voice channel')
    @commands.check(bot_voice_connected)
    async def disconnect(self, ctx):
            # Stop playback & empty queue
            await ctx.invoke(self.stop)

            voice_channel = self.vc.channel
            logger.info(f'Disconnecting from voice channel: "{voice_channel}" id={voice_channel.id}')
            await self.vc.disconnect()
            self.vc = None
            # add reaction if invoked directly
            if ctx.invoked_with == self.stop.name:
                await ctx.message.add_reaction('👋')

    @commands.command(brief='Play/Queue a song')#, aliases=['queue'])
    @commands.check(user_voice_connected)
    async def play(self, ctx, *, search):
        # Connect to channel if not connected
        if not self.vc:
            logger.info('Not connect to voice. Connecting now')
            await ctx.invoke(self.connect)

        async with ctx.typing():
            vid = await self.get_info(search)
            vid['requester'] = ctx.author
            logger.info(f'Putting "{vid["title"]}" into queue')
            self.song_queue.append(vid)

        # Start playing audio if not playing already
        if self.vc.is_playing():
            embed = discord.Embed(title="", description=f"Queueing [{vid['title']}]({vid['webpage_url']}) [{ctx.author.mention}]", color=discord.Color.blue())
        else:
            self.play_song(None)
            embed = discord.Embed(title="", description=f"Playing [{vid['title']}]({vid['webpage_url']}) [{ctx.author.mention}]", color=discord.Color.green())

        # respond
        await ctx.message.add_reaction('▶')
        await ctx.send(embed=embed)

    @commands.command(brief='Display current queue')
    @commands.check(playing)
    async def queue(self, ctx):
        embed = discord.Embed(title='Queue', description=f"**Current song:** [{self.current_song['title']}]({self.current_song['webpage_url']}) [{self.current_song['requester'].mention}]", color=discord.Colour.blue())
        song_number = 0

        # add songs
        for song in self.song_queue:
            song_number += 1
            if len(embed.description) < 4096:
                embed.description += f"\n{song_number}. [{song['title']}]({song['webpage_url']}) [{song['requester'].mention}]"
            else:
                break

        await ctx.send(embed=embed)

    @commands.command(brief='Skip current song', aliases=['next'])
    @commands.check(playing)
    async def skip(self, ctx):
        logger.info('Skipping current song')
        self.vc.stop()
        await ctx.message.add_reaction('⏭')

    @commands.command(brief='Shuffle queue')
    @commands.check(playing)
    async def shuffle(self, ctx):
        logger.info('Shuffling queue')
        shuffle(self.song_queue)
        await ctx.message.add_reaction('🔀')

    @commands.command(brief='Pause current playback')
    @commands.check(playing)
    async def pause(self, ctx):
        logger.info('Pausing playback')
        self.vc.pause()
        await ctx.message.add_reaction('⏸')

    @commands.command(brief='Resume playback')
    @commands.check(paused)
    async def resume(self, ctx):
        logger.info('Resuming playback')
        self.vc.resume()
        await ctx.message.add_reaction('▶')

    @commands.command(brief='Stop current playback and empty queue')
    @commands.check_any(commands.check(playing), commands.check(paused))
    async def stop(self, ctx):
        # Empty queue
        self.song_queue = deque()

        logger.info('Stopping playback')
        self.vc.stop()
        
        # react if called directly
        if ctx.invoked_with == self.stop.name:
            await ctx.message.add_reaction('⏹')


def setup(bot):
    bot.add_cog(Music(bot))

def teardown(bot):
    bot.remove_cog('Music')
