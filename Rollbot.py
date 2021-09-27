import logging
import time
import os

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Update

from InternalLogic import InternalLogic


class Rollbot(InternalLogic):
    """
    Класс бота. Содержит в себе обработчики сообщений. Тестировать не надо
    """
    def __init__(self, master_id: int = 351693351, rolls: dict = None):
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.INFO, filename="data/rollbot.log")
        super().__init__(master_id, rolls)
        self.start_time = time.time()
        self.global_commands = {
            'ping': self.ping,
            'r': self.simple_roll,
            'stats': self.get_stats,
            'start': self.help_handler,
            'help': self.help_handler,
            'add_global': self.add_global_command,
            'remove_global': self.remove_global_command,
            'get_globals': self.get_global_commands,
        }

    # params: update and context
    def simple_roll(self, update: Update, _, default_count=1, default_dice=20):
        text = self.get_user_name(update) + ': ' + self.process_roll(update.message.text, default_count, default_dice)
        self.reply_to_message(update, text)

    # just ping
    @staticmethod
    def ping(update, _):
        update.message.reply_text('Pong!')
        print('ping!')

    def add_global_command(self, update, _):
        msg = self.process_add_global(update.message.text, update.message.from_user.id)
        self.reply_to_message(update, msg)

    def remove_global_command(self, update, _):
        msg = self.process_remove_global(update.message.text, update.message.from_user.id)
        self.reply_to_message(update, msg)

    def get_global_commands(self, update, _):
        msg = "Global commands:"
        for shortcut, (roll_c, roll_d) in self.rolls.values():
            msg += "\n{} - {}d{}".format(shortcut, roll_c, roll_d)
        self.reply_to_message(update, msg)

    # get stats only to d20
    def get_stats(self, update, _):
        msgs = self.process_stats()
        for msg in msgs:
            self.reply_to_message(update, msg)

    def help_handler(self, update, _):
        text = """
/r - Throw dices. You can specify dice count and number of faces of each dice, for example /r 3d6 - cube for statistics check.
Specify either the number of bones (number), or the number of faces (d + number), or both combination of them, for example /r 5d8
The default roll is 1d20, there are also similar commands, with different default rolls:
/c - 3d6
/p - 1d100
A complete list of available throws can be obtained by the command /get_globals

The bot also collects statistics:
/stats - get statistics of all throws
"""
        if update.message.from_user.id == self.master_id:
            text += """
\n/add_globall /roll 1d20 - add a new global roll
\n/remove_globall /roll - remove global roll"""
        self.reply_to_message(update, text)

    def all_commands_handler(self, update, context):
        if update.message.text is None or len(update.message.text) == 0 or update.message.text[0] != '/':
            return  # Not a command
        cmd = update.message.text.split()[0][1:].replace(context.bot.name, '')
        if cmd in self.rolls:
            roll = self.rolls[cmd]
            return self.simple_roll(update, context, roll[0], roll[1])

    # log all errors
    @staticmethod
    def error_handler(update: Update, context: CallbackContext):
        logging.error('Error: {} ({} {}) caused.by {}'.format(context, type(context.error), context.error, update))
        if update is not None and update.message is not None:
            update.message.reply_text("Error")


# запуск роллбота
def init(token):
    if not os.path.exists('data'):
        os.makedirs('data')
    rollbot = Rollbot(rolls={
        'c': (3, 6),
        'p': (1, 100),
    })

    updater = Updater(token=token, use_context=True)
    # adding handlers
    for command, func in rollbot.global_commands.items():
        updater.dispatcher.add_handler(CommandHandler(command, func))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, rollbot.all_commands_handler))
    updater.dispatcher.add_error_handler(rollbot.error_handler)

    print("Started", time.time())
    updater.start_polling()
    updater.idle()
    print("Stopping")
