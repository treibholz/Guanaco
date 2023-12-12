#!/usr/bin/env python3

import logging
import configparser

from slixmpp import ClientXMPP
import requests
import json


class Conversation():
    """ Todo """
    def __init__(self, jid):
        self.jid = jid
        self.messages = []


class OllamaBot(ClientXMPP):
    def __init__(self, jid, password, ollama_url, model):
        ClientXMPP.__init__(self, jid, password)
        self.context = []
        self.conversations = {}
        self.messages = []
        self.model = model
        self.ollama_url = ollama_url
        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)

    def session_start(self, event):
        self.send_presence()
        self.get_roster()

    def reset(self):
        self.context = []
        self.messages = []
        return "SYSTEM: Context reset: start a new conversation."

    def chat(self, user_msg, jid=False):
        URL = f"{self.ollama_url}/api/chat"
        self.messages.append({"role": "user", "content": user_msg})
        query = {
            "model": self.model,
            "messages": self.messages,
            "stream": False
        }
        r = requests.post(URL, data=json.dumps(query))
        self.messages.append(r.json()['message'])
        # print(f'\n{self.messages}\n')
        return r.json()['message']['content']

    def generate(self, user_msg):
        """ Deprecated - use chat() """
        URL = f"{self.ollama_url}/api/generate"
        query = {
            "model": self.model,
            "prompt": user_msg,
            "context": self.context,
            "stream": False
        }
        r = requests.post(URL, data=json.dumps(query))
        self.context = r.json()['context']
        return r.json()['response']

    def message(self, msg):
        if msg['type'] in ('chat', 'normal'):
            # user = msg['from'].split('/')[0]
            if msg['body'].startswith('%'):
                reply = self.command(msg['body'][1:])
            else:
                reply = self.chat(f"{msg['body']}")
            msg.reply(reply).send()

    def get_local_models(self):
        URL = f"{self.ollama_url}/api/tags"
        r = requests.get(URL)
        models = r.json()['models']
        model_list = [x['name'] for x in models]
        return model_list

    def command(self, cmd):
        # this is very simple
        args = cmd.split()
        if args[0] == 'reset':
            reply = self.reset()
        elif args[0] == 'list':
            reply = "SYSTEMS: Available models:\n"
            for m in self.get_local_models():
                if m.split(':')[1] != 'latest':
                    reply += f"* {m}\n"
                else:
                    reply += f"* {m.split(':')[0]}\n"
        elif args[0] == 'model':
            if len(args) >= 2:
                self.model = args[1]
                reply = f"SYSTEM: Model set to {self.model} (keep conversation)."  # noqa: E501
            else:
                reply = f"SYSTEM: Current model: {self.model}"
        elif args[0] == 'help':
            reply = """
SYSTEM: %help - this help
        %reset - reset context (new conversation)
        %list - list locally available models
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
