# Guanaco
A simple XMPP bot for [Ollama](https://github.com/jmorganca/ollama).

Disclaimer: This is not craftmanship, but tinkering for fun. Documentation
might be wrong, out-of-date and incomplete. RTFS if in doubt.

## Configuration

```ini
[DEFAULT]

[xmpp]
jid = bot@yourjabber.org
password = supersecretpassword
resource = ollama

[ollama]
model = mistral
url = http://localhost:11434
```

## Usage

Commands start with `%`:

```
07:58:28 - me: %help
07:58:29 - Guanaco/ollama:
           SYSTEM: %help - this help
                   %reset - reset context (new conversation)
                   %model - show currently used model
                   %model <name> - switch to other model
```
