#!/usr/bin/python3
import argparse
import logging
import signal
import traceback

from discord.ext import commands

# Command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('-t', '--token', required=True, help='Discord Bot Token')
parser.add_argument('-l', '--log', default='WARNING', help='Log Level. One of [DEBUG, INFO, WARNING, ERROR, CRITICAL]. Defaults to WARNING')
parser.add_argument('-n', '--notify', action='store_true', help='Notify systemd service')
parser.add_argument('-p', '--prefix', default='$', help='Bot commands prefix')
parser.add_argument('-e', '--extension', action='extend', nargs='*', help='Name of the python file with an discord.py extension. See https://discordpy.readthedocs.io/en/stable/ext/commands/extensions.html#ext-commands-extensions')
args = parser.parse_known_args()

# systemd notifier
if args[0].notify:
    import sdnotify
    notifier = sdnotify.SystemdNotifier()

# Logging Config
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.WARNING)
NUMERIC_LOG_LEVEL = getattr(logging, args[0].log.upper(), None)
if not isinstance(NUMERIC_LOG_LEVEL, int):
    raise ValueError(f'Invalid log level: {args[0].log}')
logging.basicConfig(level=NUMERIC_LOG_LEVEL)



# Define bot
bot = commands.Bot(command_prefix=args[0].prefix, case_insensitive=True, help_command=commands.DefaultHelpCommand(verify_checks=False, no_category='Other', sort_commands=False))

# On bot ready
@bot.event
async def on_ready():
    if args[0].notify:
        notifier.notify('READY=1')
    logging.info('Logged in as')
    logging.info(f'User: {bot.user.name}')
    logging.info(f'ID: {bot.user.id}')
    logging.info('------------------')

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

# Manually load extension
@bot.command(hidden=True)
@commands.is_owner()
async def load(ctx, module):
    try:
        bot.load_extension(module)
        args[0].extension.append(module)
        logging.info(f'Loaded extension {module}')
    except Exception as e:
        await ctx.send('🛑 `{}: {}`'.format(type(e).__name__, e))
        logging.warning(f'Failed to load extension {module}')
        traceback.print_exc()
    else:
        await ctx.send(f'✅ Sucess')

# Manually unload extension
@bot.command(hidden=True)
@commands.is_owner()
async def unload(ctx, module):
    try:
        bot.unload_extension(module)
        args[0].extension.remove(module)
        logging.info(f'Unloaded extension {module}')
    except Exception as e:
        await ctx.send('🛑 `{}: {}`'.format(type(e).__name__, e))
        logging.warning(f'Failed to unload extension {module}')
        traceback.print_exc()
    else:
        await ctx.send(f'✅ Sucess')

# Manually reload extension
@bot.command(hidden=True)
@commands.is_owner()
async def reload(ctx, module=None):
    try:
        if module:
            bot.reload_extension(module)
            logging.info(f'Reloaded extension {module}')
        else:
            logging.info('Reloading all extensions')
            for extension in args[0].extension:
                bot.reload_extension(extension.removesuffix('.py'))
                logging.info(f'Reloaded extension {extension}')
    except Exception as e:
        await ctx.send('🛑 `{}: {}`'.format(type(e).__name__, e))
        logging.warning(f'Failed to reload extension {module}')
        traceback.print_exc()
        args[0].extension.remove(extension)
    else:
        await ctx.send(f'✅ Sucess')

# list modules
@bot.command(hidden=True, aliases=['extension', 'modules', 'module'])
@commands.is_owner()
async def extensions(ctx):
    await ctx.send(f'Currently loaded extensions: `{"`, `".join(list(bot.extensions.keys()))}`')



# systemd reload
def reloader(signum, frame):
    logging.info('Reloading extensions because of SIGHUP')
    for extension in args[0].extension:
        try:
            bot.reload_extension(extension.removesuffix('.py'))
            logging.info(f'Reloaded extension {extension}')
        except Exception:
            logging.warning(f'Failed to reload extension {extension}')
            traceback.print_exc()

# Validate extension names
args[0].extension = [ext.replace('/', '.').removesuffix('.py') for ext in args[0].extension]

# Load extensions
if args[0].extension:
    logging.info('Extension loading')
    for extension in args[0].extension:
        try:
            bot.load_extension(extension.removesuffix('.py'))
            logging.info(f'Loaded extension {extension}')
        except Exception:
            logging.warning(f'Failed to load extension {extension}')
            traceback.print_exc()
            args[0].extension.remove(extension)

# systemd reload
signal.signal(signal.SIGHUP, reloader)

# Run bot
bot.run(args[0].token)
