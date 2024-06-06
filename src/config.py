import configparser

config = configparser.ConfigParser()


def load_config():
    global config
    config.read("config.ini")


load_config()
