"""
Created on May 26, 2014

@author: StarlitGhost
"""
from twisted.plugin import IPlugin
from desertbot.moduleinterface import IModule
from desertbot.modules.commandinterface import BotCommand
from zope.interface import implementer

import datetime

from twisted.internet import task
from twisted.internet import reactor
from pytimeparse.timeparse import timeparse

from desertbot.message import IRCMessage
from desertbot.response import IRCResponse, ResponseType
from desertbot.utils import string


@implementer(IPlugin, IModule)
class Delay(BotCommand):
    def triggers(self):
        return ['delay', 'later']

    def help(self, query):
        return ('delay <duration> <command> (<parameters>)'
                ' - executes the given command after the specified delay')

    def execute(self, message: IRCMessage):
        if len(message.parameterList) < 2:
            return IRCResponse(ResponseType.Say, self.help(None), message.replyTo)

        command = message.parameterList[1].lower()
        delay = timeparse(message.parameterList[0])
        if not delay:
            delay = 0

        delayDelta = datetime.timedelta(seconds=delay)
        delayString = string.deltaTimeToString(delayDelta, 's')
        params = message.parameterList[2:]
        commandString = '{}{} {}'.format(self.bot.commandChar, command, ' '.join(params))
        commandString = commandString.replace('$delayString', delayString)
        commandString = commandString.replace('$delay', str(delay))

        newMessage = IRCMessage(message.type, message.user, message.channel,
                                commandString, self.bot)

        moduleHandler = self.bot.moduleHandler
        if command in moduleHandler.mappedTriggers:
            module = moduleHandler.mappedTriggers[command].execute
            d = task.deferLater(reactor, delay, module, newMessage)
            d.addCallback(self._activate)
            d.addErrback(self._deferredError)
            return IRCResponse(ResponseType.Say,
                               "OK, I'll execute that in {}".format(delayString),
                               message.replyTo,
                               {'delay': delay, 'delayString': delayString})
        else:
            if 'Alias' not in moduleHandler.commands:
                return IRCResponse(ResponseType.Say,
                                   "'{}' is not a recognized command".format(command),
                                   message.replyTo)

            if command not in moduleHandler.commands['Alias'].aliases:
                return IRCResponse(ResponseType.Say,
                                   "'{}' is not a recognized command or alias".format(command),
                                   message.replyTo)

            d = task.deferLater(reactor, delay, moduleHandler.commands['Alias'].execute, newMessage)
            d.addCallback(self._activate)
            d.addErrback(self._deferredError)
            return IRCResponse(ResponseType.Say,
                               "OK, I'll execute that in {}".format(delayString),
                               message.replyTo)

    def _activate(self, response: IRCResponse):
        if not isinstance(response, list):
            response = [response]
        self.bot.moduleHandler.sendResponses(response)

    def _deferredError(self, error):
        self.logger.exception(error)


delay = Delay()
