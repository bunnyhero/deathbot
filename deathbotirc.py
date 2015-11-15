#!/usr/bin/env python
# coding=utf8
# Copyright (c)2009 Sean Langley.  Some rights reserved.
# portions Copyright (C) 2006-2009 Eric Florenzano from the following website:
# http://www.eflorenzano.com/blog/post/writing-markov-chain-irc-bot-twisted-and-python/
#
# see the accompanying LICENSE file

import argparse

from twisted.words.protocols import irc
from twisted.internet import protocol
import random
import sys
from twisted.internet import reactor
from datetime import *
from threading import Timer
import string
#from wordwar import *
from wordwar import WordWar
from wordwar import WordWarManager
import botutils
import logging
import shlex

logger = logging.getLogger()

deatharray = []
promptarray = []

command_help = {
    "!startwar": ("# ## -> create a war lasting # minutes, starting in ## minutes", 0),
    "!throwdown": ("# ## -> create a war lasting # minutes, starting in ## minutes", 1),
    "!status": ("-> list wars that are in progress or not yet started", 2),
    "!joinwar": ("<warname> -> join a word war so you get PM'd on start", 3),
    "!leavewar": ("<warname> -> leave a word war", 4),
    "!time": ("-> what's the server time", 5),
    "!decide": ('"option 1" "option 2" ["option 3"...] -> choose randomly between options', 6),
}


def load_death_and_prompt_arrays():

    # for item in deatharray:
    #     deatharray.remove(item)

    # f = open("deathlist.txt","r")
    # print str(datetime.today()) + " | " + "Reloading Death Array"

    # for line in f.readlines():
    #     deatharray.append(line)
    #     print str(datetime.today()) + " | " + "adding "+line

    # f.close()

    for item in promptarray:
        promptarray.remove(item)

    f = open("promptlist.txt", "r")
    logger.info("Reloading Prompt Array")

    for line in f.readlines():
        promptarray.append(string.strip(line))
        logger.info("adding " + line)
    f.close()


def getRandomDeath():
    death = random.choice(deatharray)
    return death


def getRandomPrompt():
    prompt = random.choice(promptarray)
    return prompt


class WordWarBot(irc.IRCClient):

    channel = ""
    victim = "deathbot"
    victim_display = "deathbot"

    lastdeathtime = datetime.today() - timedelta(seconds=45)

    def __init__(self):
        self.wwMgr = WordWarManager(self)

    def long_enough_since_death(self):
        if ((datetime.today() - timedelta(seconds=30)) > self.lastdeathtime):
            self.lastdeathtime = datetime.today()
            return True
        else:
            return False

    def _get_nickname(self):
        return self.factory.nickname
    nickname = property(_get_nickname)

    def signedOn(self):
        self.join(self.factory.channel)
        logger.info("Signed on as %s." % (self.nickname,))

    def part_room(self):
        self.part(self.factory.channel)
        logger.info("Parted as %s." % (self.nickname,))

    def joined(self, channel):
        logger.info("Joined %s." % (channel,))
        self.channel = channel

    def check_for_daddy(self, user):
        short_user = user.split("!")[0]
        if (short_user == "bunnyhero"):
            return 1
        else:
            return 0

    def parse_echo(self, msg, user):
        commandlist = msg.split(" ", 1)
        self.irc_send_say(commandlist[1])

    def parse_do(self, msg, user):
        commandlist = msg.split(" ", 1)
        self.irc_send_describe(commandlist[1])


    def parse_changevictim(self, msg, user):
        if (self.check_for_daddy(user) == 1):
            commandlist = msg.split(" ")
            self.victim = commandlist[1].lower()
            self.victim_display = commandlist[1]
            self.irc_send_msg(user, "You have changed the victim to: " + self.victim)

    def privmsg(self, user, channel, msg):
        father = self.check_for_daddy(user)
        msg = irc.stripFormatting(msg).strip()
        lowmsg = msg.lower()

        # handle !commands
        if lowmsg.startswith('!'):
            command = lowmsg.split(' ')[0]
            if command == "!startwar" or command == "!throwdown":
                self.parse_startwar(msg, user, command)
            elif command == "!starwar":
                self.parse_starwars(msg, user)
            elif command == "!echo":
                if father == 1:
                    self.parse_echo(msg, user)
            elif command == "!do":
                if father == 1:
                    self.parse_do(msg, user)
            elif command == "!status":
                self.wwMgr.get_status(user)
            elif command == "!time":
                self.irc_send_me("thinks the time is " + datetime.today().strftime('%Y-%m-%d %I:%M:%S %p'))
            elif command == "!joinwar":
                self.parse_join_wordwar(msg, user)
            elif command == "!leavewar" or command == "!forfeit" or command == "!surrender":
                self.parse_leave_wordwar(msg, user)
            elif command == "!help":
                self.print_usage(user)
            elif command == "!reloaddeath":
                load_death_and_prompt_arrays()
            elif command == "!rejoinroom":
                self.signedOn()
            elif command == "!leaveroom":
                if (father == 1):
                    self.part_room()
            elif command == "!changevictim":
                self.parse_changevictim(msg, user)
            elif command == "!victim":
                if (father == 1):
                    self.irc_send_msg(user, "The victim is currently: " + self.victim)
            elif command == "!prompt":
                prompt = getRandomPrompt()
                # if (self.check_for_daddy(user) == 1):
                #     self.irc_send_say("Yes, father.")
                irc.IRCClient.say(self, channel, string.strip("Here's one: %s" % prompt))
            elif command == "!decide":
                self.parse_decide(msg, user)

    def parse_starwars(self, msg, user):
        logger.info(msg)
        short_user = user.split("!")[0]
        self.irc_send_say("%s: \x02Star Wars The Force Awakens\x0f opens Dec 17" % short_user)
        self.irc_send_say("(perhaps you meant to use \x02!startwar\x0f ?)")


    def parse_startwar(self, msg, user, verb_used):
        logger.info(msg)
        logger.info(user)
        short_user = user.split("!")[0]
        if self.wwMgr.check_existing_war(short_user):
            self.irc_send_msg(short_user, "Each user can only create one Word War at a time")
            return

        commandlist = [c for c in msg.split(" ") if c != '']
        if (len(commandlist) < 3):
            self.irc_send_msg(user, "Usage: %s %s " % (verb_used, command_help[verb_used][0]))
            return
        war = self.initiate_war(short_user, commandlist)
        if war is not None:
            war.add_user_to_wordwar(user)
            self.irc_send_msg(user, "You have been added to WW: %s" % (war.name,))

    def initiate_war(self, short_user, commandlist):
        war = self.wwMgr.create_word_war(short_user, commandlist[1], commandlist[2], getRandomPrompt())
        logger.info("Create word war %s length %s starting in %s", short_user, commandlist[1], commandlist[2])
        # if (self.check_for_daddy(short_user) == 1):
        #     self.irc_send_say("Yes father.")
        self.irc_send_say("The gauntlet has been thrown... "
                          + short_user + " called a word war of "
                          + botutils.minutes_string(commandlist[1]) + ", starting in "
                          + botutils.minutes_string(commandlist[2]) + ".")
        self.irc_send_say("Optional Prompt for this WW is: %s" % war.prompt)
        return war

    def parse_join_wordwar(self, command, user):
        # if (self.check_for_daddy(user) == 1):
        #     self.irc_send_say("Yes father.")
        logger.info(command)
        commandlist = [c for c in command.split(" ") if c != '']
        if len(commandlist) != 2:
            self.irc_send_msg(user, "Usage: %s %s " % (commandlist[0], command_help[commandlist[0]][0]))
            return

        war_name = commandlist[1]
        if self.wwMgr.insert_into_war(war_name, user):
            self.irc_send_msg(user, "You have been added to WW: " + war_name)
        else:
            self.irc_send_msg(user, "There is no word war named %s" % war_name)
    

    def parse_leave_wordwar(self, command, user):
        logger.info(command)
        commandlist = [c for c in command.split(" ") if c != '']
        if len(commandlist) != 2:
            self.irc_send_msg(user, "Usage: %s %s " % (commandlist[0], command_help[commandlist[0]][0]))
            return

        war_name = commandlist[1]
        if self.wwMgr.remove_from_war(war_name, user):
            self.irc_send_msg(user, "You have been removed from WW: %s" % war_name)
            if len(self.wwMgr.get_word_war_nicks(war_name)) == 0:
                self.wwMgr.cancel_word_war(war_name)
        else:
            self.irc_send_msg(user, "You are not part of word war %s" % war_name)


    def parse_decide(self, msg, user):
        """ Chooses one random option """
        short_user = user.split("!")[0]        
        msg = irc.stripFormatting(msg).strip()
        choices = shlex.split(msg)
        if len(choices) < 3:
            self.irc_send_say("%s, please provide 2 or more options" % short_user)
            return

        del choices[0]
        self.irc_send_say("%s, the dice choose: %s" % (short_user, random.choice(choices)))


    def print_usage(self, user):
        self.irc_send_msg(user, "Bot Usage:")
        # sort the help items by ordinal
        help_items = sorted(command_help.items(), key=lambda item: item[1][1])
        for help in help_items:
            self.irc_send_msg(user, help[0] + " " + help[1][0])

    def irc_send_me(self, message):
        irc.IRCClient.describe(self, self.channel, message)
        logger.info(self.channel + " -- me --> " + message)

    def irc_send_say(self, message):
        irc.IRCClient.say(self, self.channel, message)
        logger.info(self.channel + " -- say --> " + message)

    def irc_send_describe(self, message):
        irc.IRCClient.describe(self, self.channel, message)
        logger.info(self.channel + " -- describe --> " + message)

    def irc_send_msg(self, user, message):
        irc.IRCClient.msg(self, user.split("!")[0], message)
        logger.info(self.channel + " -- msg: " + user + " --> " + message)


    def action(self, user, channel, data):
        """ called when a user does something in the channel """
        logger.info("%s: user '%s' did '%s'", channel, user, data)

        short_user = user.split('!')[0]

        # did this involve the bot?
        action = irc.stripFormatting(data).lower()
        pos = action.find(self.nickname.lower())
        if pos != -1:
            verb_clause = action[0:pos].lower().strip()
            if verb_clause == "hugs":
                # hug back after a delay
                reactor.callLater(1.0, self.irc_send_me, "hugs %s" % short_user)

    def userRenamed(self, oldname, newname):
        logger.info("user '%s' renamed to '%s'", oldname, newname)
        self.wwMgr.rename_user(oldname, newname)

class WordWarBotFactory(protocol.ClientFactory):
    protocol = WordWarBot

    def __init__(self, channel, nickname='adeathbot'):
        self.channel = channel
        self.nickname = nickname

    def clientConnectionLost(self, connector, reason):
        logger.info("Lost connection (%s), reconnecting." % (reason,))
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        logger.info("Could not connect: %s" % (reason,))


def config_logger():
    log_format = '%(asctime)s %(levelname)s:%(name)s | %(message)s'
    logging.basicConfig(filename='ebot.log', format=log_format, level=logging.DEBUG)
    # add a console logger too
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter(log_format)

    # add formatter to ch
    ch.setFormatter(formatter)

    logging.getLogger().addHandler(ch)

if __name__ == "__main__":

    config_logger()

    parser = argparse.ArgumentParser(description='word war bot')
    parser.add_argument('channel', help='channel to join (without the #)')
    parser.add_argument('nick', help='nick for the bot')
    args = parser.parse_args()

    logger.info(args)

    chan = args.channel
    nick = args.nick
    load_death_and_prompt_arrays()
    reactor.connectTCP('irc.mibbit.com', 6667, WordWarBotFactory('#' + chan, nick))
    reactor.run()
