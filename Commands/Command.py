from abc import *


class Command(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def resolve(self):
        """Resolve anything dealing with the command"""
        return

    @abstractmethod
    def respond(self, target, message):
        """Respond in IRC chat for the command, if necessary"""
        return
