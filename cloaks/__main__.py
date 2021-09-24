from argparse import ArgumentParser
from asyncio  import run as asyncio_run

from ircrobots import ConnectionParams, SASLUserPass

from .       import Bot
from .config import Config, load as config_load

async def main(config: Config):
    bot = Bot(config)

    host, port, tls      = config.server
    sasl_user, sasl_pass = config.sasl

    params = ConnectionParams(
        config.nickname,
        host,
        port,
        tls,
        username=config.username,
        realname=config.realname,
        password=config.password,
        sasl=SASLUserPass(sasl_user, sasl_pass),
        autojoin=[config.channel]
    )
    await bot.add_server(host, params)
    await bot.run()

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("config")
    args   = parser.parse_args()

    config = config_load(args.config)
    asyncio_run(main(config))
