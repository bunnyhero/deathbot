
from twisted.words.protocols import irc
from twisted.internet import protocol
from random import *
import sys
from twisted.internet import reactor
from datetime import *
from threading import Timer
import string
import botutils

import logging

logger = logging.getLogger(__name__)

class WordWarManager(object):
    ww_queue = []

    def __init__(self, irc):
        self.irc = irc

    def check_existing_war(self, war_name):
        for war in self.ww_queue:
            if (war.name == war_name):
                return True
        return False

    def insert_into_war(self, war_name, user):
        logger.debug("insert %s into wordwar '%s'", user, war_name)
        for awar in self.ww_queue:
            logger.debug("checking wordwar '%s'", awar.name)
            if (awar.name.lower() == war_name):
                logger.info("Adding %s - %s", awar.name, user)
                awar.add_user_to_wordwar(user)
                return True
        logger.info("Could not find wordwar '%s'", war_name)
        return False

    def create_word_war(self, name, length, start, prompt):
        new_ww = WordWar(name, length, start, self, prompt)
        self.ww_queue.append(new_ww)
        return new_ww

    def done_word_war(self, wordwar):
        self.ww_queue.remove(wordwar)

    def get_status(self, user):
#        if (self.check_for_daddy(user) == 1):
#                self.irc_send_say("Yes father.");
        if len(self.ww_queue) == 0:
            self.irc.irc_send_msg(user, "There are no active word wars")
            return

        for ww in self.ww_queue:
            ww.status_word_war(user)

    def irc_send_me(self, message):
        self.irc.irc_send_me(message)

    def irc_send_say(self, message):
        self.irc.irc_send_say(message)

    def irc_send_msg(self, user, message):
        self.irc.irc_send_msg(user.split("!")[0], message)


class WordWar(object):

    def __init__(self, name, length, start, queue, prompt):
        logger.debug("WordWar(%s, %s, %s, %s)" % (name, length, start, prompt))
        self.nicklist = []
        self.name = name
        self.prompt = prompt
        self.length = int(length)
        self.start = int(start)
        self.timecalled = datetime.today()
        self.wwqueue = queue
        self.war_start_timer = reactor.callLater(self.start * 60, self.start_word_war)
        self.timestarted = ""
        if (int(self.start) > 2):
            self.war_warning_timer = reactor.callLater((self.start - 2) * 60, self.warning_word_war)
        self.status = 0

    def warning_word_war(self):
        self.send_message("WW: " + self.name + " starts in 2 minutes for " + botutils.minutes_string(self.length))
        self.send_message("Optional Prompt for this WW is: %s" % self.prompt)
        self.notify_nicks()

    def start_word_war(self):
        # send out message
        self.status = 1
        self.send_message(
            "GOOOOOOOOOOO!!! WW: " + self.name + " for " + botutils.minutes_string(self.length))
        self.send_message("Optional Prompt for this WW is: %s" % self.prompt)
        self.notify_nicks()
        self.timestarted = datetime.today()
        self.war_timer = reactor.callLater(float(self.length) * 60.0, self.finish_word_war)

    def status_word_war(self, user):
        self.wwqueue.irc_send_msg(user, "name: " + self.name)
        self.wwqueue.irc_send_msg(user, "length: " + botutils.minutes_string(self.length))
        if (self.status == 0):
            self.wwqueue.irc_send_msg(user, "status: waiting")
            self.wwqueue.irc_send_msg(user, "called at: " + self.timecalled.strftime('%Y-%m-%d %I:%M:%S %p'))
            interval = timedelta(minutes=self.start)
            then = self.timecalled + interval
            timeleft = then - datetime.today()
            self.wwqueue.irc_send_msg(user, "time until start: %s" % (botutils.format_timedelta(timeleft)))

        else:
            self.wwqueue.irc_send_msg(user, "status: underway")
            self.wwqueue.irc_send_msg(user, "started at: " + self.timestarted.strftime('%Y-%m-%d %I:%M:%S %p'))
            timeleft = self.timestarted + timedelta(minutes=self.length) - datetime.today()
            self.wwqueue.irc_send_msg(user, "time until end: %s" % (botutils.format_timedelta(timeleft)))

        self.wwqueue.irc_send_msg(user, "number of members: " + str(len(self.nicklist)))
        self.wwqueue.irc_send_msg(user, "-----")

    def finish_word_war(self):
        # remove from queue
        logger.info("finish word war")
        logger.info("remove from queue")
        self.send_message("WW: " + self.name + " is done - share your results")
        self.notify_nicks()

        self.wwqueue.done_word_war(self)

    def add_user_to_wordwar(self, username):
        logger.debug("add_user_to_wordwar(): ww %s, user %s", self.name, username)
        self.nicklist.append(username)
        logger.debug("ww %s nicklist now %s", self.name, self.nicklist)

    def notify_nicks(self):
        second_message = "Hey! That means you: "
        for nick in self.nicklist:
            shortnick = nick.split("!")
            second_message = second_message + shortnick[0] + " "
        self.wwqueue.irc_send_say(second_message)

    def send_message(self, message):
        self.wwqueue.irc_send_say(message)
        for nick in self.nicklist:
            self.wwqueue.irc_send_msg(nick, message)
