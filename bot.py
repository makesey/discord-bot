#!/usr/bin/python3
import asyncio
import argparse
import logging

import discord
from discord.ext import commands

# Command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-t', '--token', required=True, help='Discord Bot Token')
parser.add_argument('-l', '--log', default='WARNING', help='Log Level. One of [DEBUG, INFO, WARNING, ERROR, CRITICAL]. Defaults to WARNING')
parser.add_argument('-s', '--systemd', action='store_true', help='Bot is running as a systemd service')
parser.add_argument('-p', '--prefix', default='$', help='Bot commands prefix')
parser.add_argument('-e', '--extension', action='extend', nargs='*', help='Name of the python file with an discord.py extension. See https://discordpy.readthedocs.io/en/stable/ext/commands/extensions.html#ext-commands-extensions')
args = parser.parse_known_args()


### Logging

# Get log level
NUMERIC_LOG_LEVEL = getattr(logging, args[0].log.upper(), None)
if not isinstance(NUMERIC_LOG_LEVEL, int):
    raise ValueError(f'Invalid log level: {args[0].log}')

# Setup logger
discord.utils.setup_logging(level=NUMERIC_LOG_LEVEL, root=False)
BOT_LOGGER = logging.getLogger('discord.bot')

# systemd
if args[0].systemd:
    import signal
    from cysystemd.daemon import notify, Notification
    from cysystemd import journal
    
    # if handler is attached to root logger, all events by descendant loggers get logged
    # see note on https://docs.python.org/3.10/library/logging.html#logging.Logger.propagate
    DISCORD_LOGGER = logging.getLogger('discord')
    DISCORD_LOGGER.addHandler(journal.JournaldLogHandler())


# Bot intents
intents = discord.Intents(
    messages = True,
    voice_states = True
)

# Define bot
bot = commands.Bot(
    command_prefix = args[0].prefix,
    case_insensitive = True,
    help_command = commands.DefaultHelpCommand(
        verify_checks = False,
        no_category = 'Other',
        sort_commands = False
    ),
    intents = intents
)

# On bot ready
@bot.event
async def on_ready():
    BOT_LOGGER.info('Logged in as')
    BOT_LOGGER.info(f'User: {bot.user.name}')
    BOT_LOGGER.info(f'ID: {bot.user.id}')
    BOT_LOGGER.info('----------------------')
    if args[0].systemd:
        notify(Notification.READY)

# Global command errors
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send('This command cannot be used in private messages.')
    elif isinstance(error, commands.PrivateMessageOnly):
        await ctx.send('Please us private messages for this command.')
    elif isinstance(error, commands.NotOwner):
        await ctx.send('Sorry. You cannot use this command.')
    elif isinstance(error, commands.DisabledCommand):
        await ctx.send('Sorry. This command is disabled and cannot be used.')

# Ping-pong command
@bot.command(hidden=True)
async def ping(ctx):
    await ctx.send('Pong')

# Manually load extension
@bot.command(hidden=True)
@commands.is_owner()
async def load(ctx, module):
    try:
        await bot.load_extension(module)
        BOT_LOGGER.info(f'Loaded extension {module}')
    except Exception as e:
        await ctx.send('🛑 `{}: {}`'.format(type(e).__name__, e))
        BOT_LOGGER.exception(f'Failed to load extension {module}')
    else:
        await ctx.send(f'✅ Sucess')

# Manually unload extension
@bot.command(hidden=True)
@commands.is_owner()
async def unload(ctx, module):
    try:
        await bot.unload_extension(module)
        BOT_LOGGER.info(f'Unloaded extension {module}')
    except Exception as e:
        await ctx.send('🛑 `{}: {}`'.format(type(e).__name__, e))
        BOT_LOGGER.exception(f'Failed to unload extension {module}')
    else:
        await ctx.send(f'✅ Sucess')

# Manually reload extension
@bot.command(hidden=True)
@commands.is_owner()
async def reload(ctx, module=None):
    try:
        if module:
            await bot.reload_extension(module)
            BOT_LOGGER.info(f'Reloaded extension {module}')
        else:
            BOT_LOGGER.info('Reloading all extensions')
            for extension in list(bot.extensions.keys()):
                await bot.reload_extension(extension.removesuffix('.py'))
                BOT_LOGGER.info(f'Reloaded extension {extension}')
    except Exception as e:
        await ctx.send('🛑 `{}: {}`'.format(type(e).__name__, e))
        BOT_LOGGER.exception(f'Failed to reload extension {module}')
    else:
        await ctx.send(f'✅ Sucess')

# list modules
@bot.command(hidden=True, aliases=['extension', 'modules', 'module'])
@commands.is_owner()
async def extensions(ctx):
    await ctx.send(f'Currently loaded extensions: `{"`, `".join(list(bot.extensions.keys()))}`')

@bot.command(aliases=['github'], brief='Source Code')
async def source(ctx):
    await ctx.send('https://github.com/makesey/discord-bot')



# systemd reload
def reloader(signum, frame):
    BOT_LOGGER.info('Reloading extensions because of SIGHUP')
    for extension in list(bot.extensions.keys()):
        try:
            asyncio.run(bot.reload_extension(extension.removesuffix('.py')))
            BOT_LOGGER.info(f'Reloaded extension {extension}')
        except Exception:
            BOT_LOGGER.exception(f'Failed to reload extension {extension}')


if args[0].extension:
    # Validate extension names
    args[0].extension = [ext.replace('/', '.').removesuffix('.py') for ext in args[0].extension]
    
    # Load extensions
    BOT_LOGGER.info('Extension loading')
    for extension in args[0].extension:
        try:
            asyncio.run(bot.load_extension(extension.removesuffix('.py')))
            BOT_LOGGER.info(f'Loaded extension {extension}')
        except Exception:
            BOT_LOGGER.exception(f'Failed to load extension {extension}')
            args[0].extension.remove(extension)

# systemd reload
if args[0].systemd:
    signal.signal(signal.SIGHUP, reloader)

# Run bot
bot.run(args[0].token, log_handler=None)
