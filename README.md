# discord-bot

>modular discord-bot written in python

## Requirements
[discord.py](https://discordpy.readthedocs.io/en/stable/index.html)  
For install instructions see [Installing](https://discordpy.readthedocs.io/en/stable/intro.html#installing)

## Usage
```shell
bot.py -t TOKEN [OPTIONAL ARGUMENTS]
```

required arguments:  
`-t TOKEN, --token TOKEN`

optional arguments:  
`-e [EXTENSION ...], --extension [EXTENSION ...]` Name of the python file with an discord.py extension.  
`-p PREFIX, --prefix PREFIX` Commands prefix  
`-s, --systemd` Bot is running as a systemd service  
`-l LOG, --log LOG` Log Level. One of [DEBUG, INFO, WARNING, ERROR, CRITICAL]. Defaults to WARNING  
`-h, --help` show this help message and exit  

## Extensions

Extra commands can be added to the bot using a discord.py extension. On startup the bot loads all extensions provided by the `-e, --extension` flag.

Once the bot is running you can load and reload extensions using commands send to the bot.

For writing extensions, see [discord.py Documentation](https://discordpy.readthedocs.io/en/stable/ext/commands/extensions.html)

## Creating a Bot Account

See [discord.py Documentation](https://discordpy.readthedocs.io/en/stable/discord.html)

## Commands

The default prefix is `$`. It can be changed by providing the `-p, --prefix` flag.

Owner only:
* `$load` load an extension
* `$unload` unload an extension
* `$reload` reload an extension, reload all if no argument given
* `$extensions` list all loaded extensions

Everyone:
* `$source` link to github page

## Extensions

### [totpal](ext/totpal.py)

Optional command-line arguments:  
`-r, --reset` Game reset timer in sec. Defaults to 7200

Commands:  
* `$set` Set your article
* `$my` Get your current article
* `$random` Get a random article, which is not yours
* `$players` Show the current players
* `$leave` Leave the game
* `$reset` Reset the game

### [misc](ext/misc.py)

Commands:
* `$coin` Flip a coin
* `$roll` Roll a die

## Systemd

Requires [cysystemd](https://pypi.org/project/cysystemd/)

To configure the bot as a sytemd-service, copy or move the file `discord-bot.service` to `/etc/systemd/system`. Replace the values for `User`, `Group`, `/path/to/bot.py` and `YOUR_TOKEN_HERE` accordingly.
