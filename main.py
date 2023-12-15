#!/usr/bin/env python3

import os
import logging
import configparser
import json

from slixmpp import ClientXMPP
import requests


class Conversations():
    def __init__(self, filename="cache.json"):
        self.filename = filename
        if os.path.isfile(filename):
            self.messages = json.load(open(filename))
        else:
            self.messages = {}

    def append_message(self, jid, message):
        if jid not in self.messages.keys():
            self.reset(jid)
        self.messages[jid].append(message)

    def reset(self, jid):
        self.messages[jid] = []

    def get_messages(self, jid):
        return self.messages[jid]

    def dump_cache(self):
        json.dump(self.messages, open(self.filename, 'w'), indent=2)


class BotCommands():
    def __init__(self, bot):
        self.b = bot
        self.pre = "*SYSTEM*"

    def help(self, unknown=False):
        if unknown:
            reply = f"{self.pre} unknown command\n"
        else:
            reply = f"\n{self.pre}\n"
        reply += "Usage:\n"
        reply += "   %help - this help\n"
        reply += "   %reset - reset context (new conversation)\n"
        reply += "   %list - list locally available models\n"
        reply += "   %model - show currently used model\n"
        reply += "   %model <name> - switch to other model, new context\n"
        reply += "   %model <name> [keep] - switch to other model, keep context\n"  # noqa: E501
        return reply

    def reset(self, jid):
        self.b.c.reset(jid)
        return f"{self.pre} Conversation reset. Let's start from the beginning with model '{self.b.model}."  # noqa: E501

    def list_models(self):
        reply = f"{self.pre} Available models:\n"
        for m in self.b.get_local_models():
            if m.split(':')[1] != 'latest':
                reply += f"  * {m}\n"
            else:
                reply += f"  * {m.split(':')[0]}\n"
        return reply

    def model(self, jid, args):
        keep = False
        if len(args) >= 1:
            if self.b.admin == jid:
                if len(args) >= 2 and args[1] == 'keep':
                    keep = True
                self.b.model = args[0]
                reply = f"{self.pre} Model set to {self.b.model}"
                if keep:
                    reply += " (keep conversation)."
                else:
                    self.b.c.reset(jid)
                    reply += " (NEW conversation)."

            else:
                reply = f"{self.pre} You are not allowed to do that"  # noqa: E501
        else:
            reply = f"{self.pre} Current model: {self.b.model}"
        return reply


class OllamaBot(ClientXMPP):
    def __init__(self, jid, password, ollama_url, model, admin):
        ClientXMPP.__init__(self, jid, password)
        self.register_plugin('xep_0085')  # ChatState
        self.c = Conversations()
        self.CMD = BotCommands(self)
        self.model = model  # Global model?
        self.admin = admin
        self.ollama_url = ollama_url
        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)

    def session_start(self, event):
        self.send_presence()
        self.get_roster()

    def chat(self, jid, user_msg):
        URL = f"{self.ollama_url}/api/chat"
        self.c.append_message(jid, {"role": "user", "content": user_msg})
        query = {
            "model": self.model,
            "messages": self.c.get_messages(jid),
            "stream": False
        }
        # print(query)
        r = requests.post(URL, data=json.dumps(query))
        self.c.append_message(jid, r.json()['message'])
        return r.json()['message']['content']

    def message(self, msg):
        if msg['type'] in ('chat', 'normal'):
            user_jid = msg['from'].bare
            if msg['body'].startswith('%'):
                reply = self.command(user_jid, msg['body'][1:])
            else:
                reply = self.chat(user_jid, f"{msg['body']}")
            msg.reply(reply).send()
            self.c.dump_cache()

    def get_local_models(self):
        URL = f"{self.ollama_url}/api/tags"
        r = requests.get(URL)
        models = r.json()['models']
        model_list = [x['name'] for x in models]
        return model_list

    def command(self, jid, cmd):
        # this is very simple
        args = cmd.split()
        if args[0] == 'reset':
            reply = self.CMD.reset(jid)
        elif args[0] == 'list':
            reply = self.CMD.list_models()
        elif args[0] == 'model':
            reply = self.CMD.model(jid, args[1:])
        elif args[0] == 'help':
            reply = self.CMD.help()
        else:
            reply = self.CMD.help(True)
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
    admin = config["DEFAULT"]["admin"]

    xmpp = OllamaBot(xmpp_user, xmpp_pass, ollama_url, ollama_model, admin)
    xmpp.connect()
    xmpp.process(forever=True)
