#!/usr/bin/env python3

import logging
import configparser

from slixmpp import ClientXMPP
import requests
import json


class OllamaBot(ClientXMPP):

    def __init__(self, jid, password, ollama_url, model):
        ClientXMPP.__init__(self, jid, password)
        self.context = []
        self.model = model
        self.ollama_url = ollama_url
        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)

    def session_start(self, event):
        self.send_presence()
        self.get_roster()

    def message(self, msg):
        URL = f"{self.ollama_url}/api/generate"

        if msg['type'] in ('chat', 'normal'):
            if msg['body'].startswith('%'):
                reply = self.command(msg['body'][1:])
            else:
                query = {
                    "model": self.model,
                    "prompt": f"{msg['body']}",
                    "context": self.context,
                    "stream": False
                }
                r = requests.post(URL, data=json.dumps(query))
                self.context = r.json()['context']
                reply = r.json()['response']
            msg.reply(reply).send()

    def command(self, cmd):
        # this is very simple
        args = cmd.split()
        if args[0] == 'reset':
            self.context = []
            reply = "SYSTEM: Context reseted"
        elif args[0] == 'model':
            if len(args) >= 2:
                self.model = args[1]
                self.context = []
                reply = f"SYSTEM: Model set to {self.model} (this includes a context reset)."  # noqa: E501
            else:
                reply = f"SYSTEM: Current model: {self.model}"
        elif args[0] == 'help':
            reply = """
SYSTEM: %help - this help
        %reset - reset context (new conversation)
        %model - show currently used model
        %model <name> - switch to other model
"""
        else:
            reply = "SYSTEM: unknown command, look at %help"
        return reply


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('config.ini')

    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)-8s %(message)s')

    xmpp_user = f'{config["xmpp"]["jid"]}/{config["xmpp"]["resource"]}'
    xmpp_pass = config["xmpp"]["password"]
    ollama_url = config["ollama"]["url"]
    ollama_model = config["ollama"]["model"]

    xmpp = OllamaBot(xmpp_user, xmpp_pass, ollama_url, ollama_model)
    xmpp.connect()
    xmpp.process(forever=True)
