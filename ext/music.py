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


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = deque()

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

    def play_song(self, vc):
        if len(self.queue) == 0: return

        # Get next song
        vid = self.queue.popleft()
        logger.info(f'Getting "{vid["title"]}" from queue')

        source = self.create_source(vid)

        logger.info(f"Playing song {vid['title']}")
        # after: use anonymous lambda function to run function with parameter
        vc.play(source, after=lambda _: self.play_song(vc))

    # Connect
    @commands.command(brief='Connect to a voice channel')
    async def connect(self, ctx):
        try:
            voice_channel = ctx.author.voice.channel
            logger.info(f'Connecting to voice channel: {voice_channel} id={voice_channel.id}')
            await voice_channel.connect()
            
            # react if called directly
            if ctx.invoked_with == self.connect.name:
                await ctx.message.add_reaction('✅')

        except AttributeError:
            logger.exception('Cannot connect. No voice channel found.')
            await ctx.send('You have to be in a voice channel for this command to work')

    @commands.command(brief='Disconnect from a voice channel')
    async def disconnect(self, ctx):
        try:
            # Stop playback & empty queue
            await ctx.invoke(self.stop)

            voice_channel = ctx.voice_client.channel
            logger.info(f'Disconnecting from voice channel: {voice_channel} id={voice_channel.id}')
            await ctx.voice_client.disconnect()
            await ctx.message.add_reaction('👋')
        except AttributeError:
            logger.exception('Cannot disconnect. Bot is not in a voice channel.')
            await ctx.send('I am currently not in a voice channel')

    @commands.command(brief='Play/Queue a song', aliases=['queue'])
    async def play(self, ctx, *, search):
        # Connect to channel if not connected
        if not ctx.voice_client:
            logger.info('Not connect to voice. Connecting now')
            await ctx.invoke(self.connect)
        vc = ctx.voice_client

        async with ctx.typing():
            vid = await self.get_info(search)
            logger.info(f'Putting "{vid["title"]}" into queue')
            self.queue.append(vid)

        # Start playing audio if not playing already
        if vc.is_playing():
            embed = discord.Embed(title="", description=f"Queueing [{vid['title']}]({vid['webpage_url']}) [{ctx.author.mention}]", color=discord.Color.blue())
        else:
            self.play_song(vc)
            embed = discord.Embed(title="", description=f"Playing [{vid['title']}]({vid['webpage_url']}) [{ctx.author.mention}]", color=discord.Color.green())

        # respond
        await ctx.message.add_reaction('▶')
        await ctx.send(embed=embed)

    @commands.command(brief='Skip current song', aliases=['next'])
    async def skip(self, ctx):
        vc = ctx.voice_client

        if vc.is_playing():
            logger.info('Skipping current song')
            vc.stop()
            await ctx.message.add_reaction('⏭')
        else:
            await ctx.send("Not playing anything")

    @commands.command(brief='Shuffle queue')
    async def shuffle(self, ctx):
        logger.info('Shuffling queue')
        shuffle(self.queue)
        await ctx.message.add_reaction('🔀')

    @commands.command(brief='Pause current playback')
    async def pause(self, ctx):
        vc = ctx.voice_client

        if vc.is_playing():
            vc.pause()
            logger.info('Pausing playback')
            await ctx.message.add_reaction('⏸')
        else:
            await ctx.send('Currently not playing audio')

    @commands.command(brief='Resume playback')
    async def resume(self, ctx):
        vc = ctx.voice_client

        if vc.is_paused():
            vc.resume()
            logger.info('Resuming playback')
            await ctx.message.add_reaction('▶')
        else:
            await ctx.send('Cannot resume')

    @commands.command(brief='Stop current playback and empty queue')
    async def stop(self, ctx):
        # Empty queue
        self.queue = deque()

        vc = ctx.voice_client
        if vc.is_playing():

            vc.stop()
            logger.info('Stopping playback')
            
            # react if called directly
            if ctx.invoked_with == self.stop.name:
                await ctx.message.add_reaction('⏹')
        else:
            if ctx.invoked_with == self.stop.name:
                await ctx.send('Currently not playing audio')



def setup(bot):
    bot.add_cog(Music(bot))
