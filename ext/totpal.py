import argparse
import logging
import random
from threading import Timer
from typing import KeysView

from discord.ext import commands

# Logger
logger = logging.getLogger(__name__)

# Dummy Timer
# needed so on_command() doesn't complain reset_timer doesn't exist
reset_timer = Timer(0.0, None)
reset_timer.name = 'Dummy timer'

# Totpal Game class
class Game:
    def __init__(self):
        self.d = {}

    def add(self, user, article):
        """Add/update a player's article"""
        logger.info(f'Set Article: {user}: {article}')
        self.d[user] = article

    def remove(self, user):
        """Remove a player from the game"""
        logger.info(f'Remove player: {user}')
        del self.d[user]

    def my(self, user):
        """Show a players article"""
        return self.d[user]

    def random(self, user):
        """Return a random article"""
        r = random.choice(list(self.d.items()))
        if r[0] != user:
            logger.info(f'Random article: {r[1]}')
            return r[1]
        else:
            return self.random(user)

    def reset(self, auto=False):
        """Reset the game"""
        if auto:
            logger.info(f'Game automaticlly reset after {args[0].reset} seconds')
        else:
            logger.info('Game manually reset')
        self.d = {}

    def players(self) -> KeysView:
        """Return players"""
        return self.d.keys()

    def number_of_players(self):
        """Return the number of players"""
        return len(self.players())

# Totpal game commands
class Totpal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Initialize game
        self.g = Game()
        logger.info('Game initialized')

    # Automatic reset
    @commands.Cog.listener()
    async def on_command(self, ctx):
        global reset_timer
        
        # Canceling previous timer
        logger.debug(f'Canceling reset timer {reset_timer.name}')
        reset_timer.cancel()

        # Create new timer
        reset_timer = Timer(args[0].reset, self.g.reset, kwargs={'auto': True})
        reset_timer.daemon = True # prevents program lockup when systemd sends SIGTERM

        # Start new timer
        logger.debug(f'Starting new reset timer {reset_timer.name} lasting {args[0].reset} seconds')
        reset_timer.start()

    # Ping-pong command
    @commands.command(hidden=True)
    async def ping(self, ctx):
        await ctx.send('Pong')

    # Set article
    @commands.command(name='set', aliases=['SetMyArticle', 'sma', 'SetArticle', 'sa',], brief='Set your article', usage='Name of Article')
    @commands.dm_only()
    async def set_article(self, ctx, *args):
        if args == ():
            await ctx.send('Need to supply an article')
        else:
            article = ' '.join(args)
            self.g.add(ctx.author, article)
            await ctx.send(f'Your article is: {article}')

    # Get player article
    @commands.command(name='my', aliases=['GetMyArticle', 'gma', 'GetArticle', 'ga', 'MyArticle', 'ma',], brief='Get your current article')
    @commands.dm_only()
    async def get_article(self, ctx):
        try:
            await ctx.send(f'Your article is: {self.g.my(ctx.author)}')
        except KeyError:
            await ctx.send('You currently have no article')

    # Get article: Reply privatly
    @get_article.error
    async def my_article_error(self, ctx, error):
        if isinstance(error, commands.PrivateMessageOnly):
            await ctx.author.send(f'Your article is: {self.g.my(ctx.author)}')
            await ctx.send("I replied to you privatly so the other players don't see your article")

    # Get random article
    # TODO: ping players
    @commands.command(name='random', aliases=['GetRandomArticle', 'gra', 'GetRandom', 'gr'], brief='Get a random article, which is not yours')
    @commands.guild_only()
    async def get_random(self, ctx):
        if self.g.number_of_players() < 3:
            await ctx.send(f'To few players to start the game. Only {self.g.number_of_players()} of at least 3 players.')
        else:
            await ctx.send(f'Random article is: {self.g.random(ctx.author)}')

    # Leave game
    @commands.command(aliases=['exit'], brief='Leave the game')
    async def leave(self, ctx):
        try:
            self.g.remove(ctx.author)
            await ctx.send('You left the game')
        except KeyError:
            await ctx.send('You are currently not participating in this game')

    # Show players
    @commands.command(brief='Show the current players')
    async def players(self, ctx):
        if self.g.number_of_players() == 0:
            await ctx.send('Currently no players')
        else:
            await ctx.send(', '.join(i.display_name for i in list(self.g.players())))

    # Reset game
    @commands.command(brief='Reset the game')
    async def reset(self, ctx):
        self.g.reset()
        await ctx.send('Game reset')


def setup(bot):
    # Argument parser
    global parser
    global args
    parser = argparse.ArgumentParser('totpal')
    parser.add_argument('-r', '--reset', default=7200.0, type=float, help='Game reset timer in sec. Defaults to 7200')
    args = parser.parse_known_args()

    # Add cog
    bot.add_cog(Totpal(bot))

def teardown(bot):
    reset_timer.cancel()
