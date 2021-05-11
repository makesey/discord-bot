# discord-bot

>modular discord-bot written in python

## Requirements
[discord.py](https://discordpy.readthedocs.io/en/stable/index.html)

For install instructions see [Installing](https://discordpy.readthedocs.io/en/stable/intro.html#installing)

## Usage
```shell
bot.py -t TOKEN -e [EXTENSION ...] [OPTIONAL ARGUMENTS]
```

required arguments:  
`-t TOKEN, --token TOKEN`

optional arguments:  
`-h, --help` show this help message and exit  
`-n, --notify` Notify systemd service  
`-l LOG, --log LOG` Log Level. One of [DEBUG, INFO, WARNING, ERROR, CRITICAL]. Defaults to WARNING  
`-p PREFIX, --prefix PREFIX` Commands prefix  
`-e [EXTENSION ...], --extension [EXTENSION ...]` Name of the python file with an discord.py extension.

## Extensions

Extra commands can be added to the bot using a discord.py extension. On startup the bot loads all extensions provided by the `-e, --extension` flag.

Once the bot is running you can load and reload extensions using commands send to the bot.

For writing extensions, see discord.py [Documentation](https://discordpy.readthedocs.io/en/stable/ext/commands/extensions.html#ext-commands-extensions)

## Creating a Bot Account

See discord.py [Documentation](https://discordpy.readthedocs.io/en/stable/discord.html)

## Commands

The default prefix is `$`. It can be changed by providing the `-p, --prefix` flag.

* `$load` load an extension
* `$unload` unload an extension
* `$reload` reload an extension, reload all if no argument given
* `$extensions` list all loaded extensions

## Systemd

To configure the bot as a sytemd-service, copy or move the file `discord-bot.service` to `/etc/systemd/system`. Replace the values for "User"and "Group". In "ExecStart", change the `/path/to/bot.py` to the path of your local bot.py and replace your "YOUR_TOKEN_HERE" with your bot token.
