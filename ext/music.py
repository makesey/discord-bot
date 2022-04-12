import asyncio
from collections import deque
import logging
from random import shuffle

import discord
from discord.ext import commands
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
        self.queue = deque()
        self.vc = None

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
        if len(self.queue) == 0: return

        # Get next song
        vid = self.queue.popleft()
        logger.info(f'Getting "{vid["title"]}" from queue')

        source = self.create_source(vid)

        logger.info(f"Playing song {vid['title']}")
        self.vc.play(source, after=self.play_song)


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
            await ctx.message.add_reaction('👋')

    @commands.command(brief='Play/Queue a song', aliases=['queue'])
    @commands.check(user_voice_connected)
    async def play(self, ctx, *, search):
        # Connect to channel if not connected
        if not self.vc:
            logger.info('Not connect to voice. Connecting now')
            await ctx.invoke(self.connect)

        async with ctx.typing():
            vid = await self.get_info(search)
            logger.info(f'Putting "{vid["title"]}" into queue')
            self.queue.append(vid)

        # Start playing audio if not playing already
        if self.vc.is_playing():
            embed = discord.Embed(title="", description=f"Queueing [{vid['title']}]({vid['webpage_url']}) [{ctx.author.mention}]", color=discord.Color.blue())
        else:
            self.play_song(None)
            embed = discord.Embed(title="", description=f"Playing [{vid['title']}]({vid['webpage_url']}) [{ctx.author.mention}]", color=discord.Color.green())

        # respond
        await ctx.message.add_reaction('▶')
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
        shuffle(self.queue)
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
        self.queue = deque()

        logger.info('Stopping playback')
        self.vc.stop()
        
        # react if called directly
        if ctx.invoked_with == self.stop.name:
            await ctx.message.add_reaction('⏹')


def setup(bot):
    bot.add_cog(Music(bot))
