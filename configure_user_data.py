#!/usr/bin/env python3

from configparser import ConfigParser
from os import makedirs
from os.path import exists, expanduser, join

CONFIGDIR = join(expanduser('~'), '.config', 'LexisNexisCrawler')
makedirs(CONFIGDIR, exist_ok=True)
CONFIGFILE = join(CONFIGDIR, 'users')


def get_value(prompt, conversion=str):
    """
    Retrieves a value and converts into the given datatype using the
    conversion function.
    """
    while True:
        try:
            value = input(prompt+' ')
            return conversion(value)
        except ValueError:
            print("The value you entered it not viable.")


def tobool(value: str):
    value = value.lower().strip()
    if value in ['true', 'y', 'yes', 'on', '1']:
        return True
    if value in ['fales', 'n', 'no', 'off', '0']:
        return False

    raise ValueError


def main():
    parser = ConfigParser()
    if exists(CONFIGFILE):
        parser.read(CONFIGFILE)
    else:
        parser['userdata'] = {}

    user_dict = parser['userdata']

    while get_value("There are {} users stored. Do you want to add "
                    "one? (y/n)".format(len(user_dict)), tobool):
        user = get_value("Enter username:")
        password = get_value("Enter password for '{}':".format(user))
        user_dict[user] = password

    with open(CONFIGFILE, 'w') as configfile:
        parser.write(configfile)

if __name__ == '__main__':
    try:
        main()
    except EOFError:
        print("Found EOF. Quitting gracefully.")
    except KeyboardInterrupt:
        print("Keyboard interrupt!")
        exit(130)
