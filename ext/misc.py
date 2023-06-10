import logging
import random

from discord.ext import commands

# Logger
logger = logging.getLogger('discord.bot').getChild(__name__)

class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Flip a coin
    @commands.command(aliases=['flip'], brief='Flip a coin')
    async def coin(self, ctx):
        if random.randint(0, 1) == 1:
            await ctx.send('Heads')
        else:
            await ctx.send('Tails')

    # Roll a dice
    @commands.command(name='roll', aliases=['dice', 'die'], brief='Roll a die', usage='NdN±N', help='Defaults to a normal 6-sided die')
    async def roll_dice(self, ctx, *args):
        try:
            # Default to 1d6+0
            if args == ():
                number_of_die = 1
                sides = 6
                modifier = 0

            # Parse user input
            else:
                user_input = ''.join(args).lower()
                if '+' in user_input:
                    dice, modifier = user_input.split('+')
                elif '-' in user_input:
                    dice, modifier = user_input.split('-')
                    modifier = int(modifier) * -1
                else:
                    dice = user_input
                    modifier = 0

                number_of_die, sides = dice.split('d')
                if number_of_die == '':
                    number_of_die = '1'
            
            # Calculate result
            result = 0
            for _ in range(int(number_of_die)):
                result += random.randint(1, int(sides))
            result += int(modifier)
            
            # Log and send
            logger.info(f'Dice: {number_of_die}, Sides: {sides}, Modifier: {modifier}, Result: {result}')
            await ctx.send(result)
        
        # Wrong format
        except ValueError:
            await ctx.send('Format has to be in NdN±N')


async def setup(bot):
    await bot.add_cog(Miscellaneous(bot))