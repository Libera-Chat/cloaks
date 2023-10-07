import asyncio, re
from hashlib import sha1
from re      import compile as re_compile

from irctokens import build, Line
from ircstates import User
from ircrobots import Bot as BaseBot
from ircrobots import Server as BaseServer
from ircrobots import ConnectionParams

from ircstates.numerics import *
from ircrobots.matching import Response, ANY, Folded, SELF
from ircrobots.glob     import Glob, compile as gcompile
from ircchallenge       import Challenge

from .config import Config

# not in ircstates yet...
RPL_RSACHALLENGE2      = "740"
RPL_ENDOFRSACHALLENGE2 = "741"
RPL_YOUREOPER          = "381"

RE_INVALID = re_compile("[^a-zA-Z0-9-_]")

def _hash(s: str, digits: int) -> str:
    hash  = int(sha1(s.encode("utf8")).hexdigest(), 16)
    hash %= (10**digits)           # n decimal digits
    return str(hash).zfill(digits) # zero-pad for short hashes

def _sanitise(s: str) -> str:
    valid = RE_INVALID.sub("", s)   # no invalid chars
    valid = valid.strip("_")        # no leading/trailing _
    valid = valid.replace("_", "-") # '_' -> '-'
    return valid

class Server(BaseServer):
    def __init__(self,
            bot:    BaseBot,
            name:   str,
            config: Config):

        super().__init__(bot, name)
        self._config  = config

    def set_throttle(self, rate: int, time: float):
        # turn off throttling
        pass

    async def _oper_up(self,
            oper_name: str,
            oper_file: str,
            oper_pass: str):

        try:
            challenge = Challenge(keyfile=oper_file, password=oper_pass)
        except Exception:
            traceback.print_exc()
        else:
            await self.send(build("CHALLENGE", [oper_name]))
            challenge_text = Response(RPL_RSACHALLENGE2,      [SELF, ANY])
            challenge_stop = Response(RPL_ENDOFRSACHALLENGE2, [SELF])
            #:lithium.libera.chat 740 sandcat :foobarbazmeow
            #:lithium.libera.chat 741 sandcat :End of CHALLENGE

            while True:
                challenge_line = await self.wait_for({
                    challenge_text, challenge_stop
                })
                if challenge_line.command == RPL_RSACHALLENGE2:
                    challenge.push(challenge_line.params[1])
                else:
                    retort = challenge.finalise()
                    await self.send(build("CHALLENGE", [f"+{retort}"]))
                    break

    async def line_read(self, line: Line):
        if line.command == RPL_WELCOME:
            await self.send(build("MODE", [self.nickname, "+g"]))
            oper_name, oper_file, oper_pass = self._config.oper
            await self._oper_up(oper_name, oper_file, oper_pass)

        elif line.command == RPL_YOUREOPER:
            await self.send(build("MODE", [self.nickname, "-s"]))

        elif (line.command == "JOIN"
                and line.source is not None
                and not self.is_me(line.hostmask.nickname)
                and not (account := line.params[1]) == "*"
                and (
                    not "/" in line.hostmask.hostname
                    or line.hostmask.hostname.startswith("gateway/")
                )):

            if not await self._cloak(account):
                await self.send(build("PRIVMSG", [
                    self._config.channel,
                    f"{nick}: your account name cannot be cloaked"
                ]))

        elif (line.command == "CHGHOST" and
                line.params[1].startswith("user/")):

            await self.send(build("KICK", [
                self._config.channel,
                line.hostmask.nickname,
                "You've been cloaked"
            ]))

            cloak = line.params[1]
            channel = self._config.channel
            nick = line.hostmask.nickname
            message = self._config.message.safe_substitute(cloak=cloak, channel=channel, nick=nick)

            if message:
                await self.send(build("NOTICE", [
                    nick,
                    message
                ]))

    async def _cloak(self, account):
        clean = _sanitise(account)
        if not clean == "":
            cloak = f"user/{clean}"
            if not account == clean:
                hash   = _hash(account, 7)
                cloak += f"/x-{hash}"

            await self.send(build("PRIVMSG", ["NickServ", f"VHOST {account} ON {cloak} FORCE"]))
            return True
        else:
            return False

    def line_preread(self, line: Line):
        print(f"< {line.format()}")
    def line_presend(self, line: Line):
        print(f"> {line.format()}")

class Bot(BaseBot):
    def __init__(self, config: Config):
        super().__init__()
        self._config = config

    def create_server(self, name: str):
        return Server(self, name, self._config)

