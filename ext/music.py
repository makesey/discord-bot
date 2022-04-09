import asyncio
import logging

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
            voice_channel = ctx.voice_client.channel
            logger.info(f'Disconnecting from voice channel: {voice_channel} id={voice_channel.id}')
            await ctx.voice_client.disconnect()
            await ctx.message.add_reaction('👋')
        except AttributeError:
            logger.exception('Cannot disconnect. Bot is not in a voice channel.')
            await ctx.send('I am currently not in a voice channel')

    @commands.command(brief='Play a song')
    async def play(self, ctx, *, search):
        vc = ctx.voice_client
        
        # Connect to channel if not connected
        if not vc:
            logger.info('Not connect to voice. Connecting now')
            await ctx.invoke(self.connect)
            vc = ctx.voice_client

        # Notify if already playing audio and exit
        if vc.is_playing():
            logger.info('Already playing audio')
            await ctx.send('Already playing audio')
            return

        try:
            # get info from youtube-dl
            async with ctx.typing():
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

            # create audio source
            logger.info('Creating audio source')
            if vid['acodec'] == 'opus':
                source = discord.FFmpegOpusAudio(vid['url'], codec='copy')
            else:
                source = discord.FFmpegOpusAudio(vid['url'])

            # play audio
            logger.info('Playing audio')
            vc.play(source)

            # respond
            embed = discord.Embed(title="", description=f"Playing [{vid['title']}]({vid['webpage_url']}) [{ctx.author.mention}]", color=discord.Color.green())
            await ctx.message.add_reaction('▶')
            await ctx.send(embed=embed)
        except Exception as e:
            logger.exception('Something went wrong')

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

    @commands.command(brief='Stop current playback')
    async def stop(self, ctx):
        vc = ctx.voice_client

        if vc.is_playing():
            vc.stop()
            logger.info('Stopping playback')
            await ctx.message.add_reaction('⏹')
        else:
            await ctx.send('Currently not playing audio')



def setup(bot):
    bot.add_cog(Music(bot))
