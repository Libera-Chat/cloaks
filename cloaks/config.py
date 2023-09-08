from dataclasses import dataclass
from os.path     import expanduser
from re          import compile as re_compile
from string      import Template
from typing      import List, Pattern, Tuple

import yaml

@dataclass
class Config(object):
    server:   str
    nickname: str
    username: str
    realname: str
    password: str
    channel:  str
    message:  Template

    sasl: Tuple[str, str]
    oper: Tuple[str, str]

def load(filepath: str):
    with open(filepath) as file:
        config_yaml = yaml.safe_load(file.read())

    nickname = config_yaml["nickname"]
    message  = Template(config_yaml.get("message", ""))

    oper_name = config_yaml["oper"]["name"]
    oper_file = expanduser(config_yaml["oper"]["file"])
    oper_pass = config_yaml["oper"]["pass"]

    return Config(
        config_yaml["server"],
        nickname,
        config_yaml.get("username", nickname),
        config_yaml.get("realname", nickname),
        config_yaml["password"],
        config_yaml["channel"],
        message,
        (config_yaml["sasl"]["username"], config_yaml["sasl"]["password"]),
        (oper_name, oper_file, oper_pass),
    )
