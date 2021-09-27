import logging
import time
import os

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Update

import rollbot_secret_token
from helper_functions import Helper
from database import CustomRoll, GlobalRoll


class Rollbot(Helper):
    def __init__(self):
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.INFO, filename="data/rollbot.log")
        super().__init__()
        self.start_time = time.time()
        self.pending_rolls = []
        self.global_commands = {
            'ping': self.ping,
            'r': self.simple_roll,
            'c': self.custom_roll_wrapper(3, 6),
            'd': self.equation_roll,
            'stats': self.get_stats,
            'statsall': self.get_full_stats,
            'start': self.help_handler,
            'help': self.help_handler,
            'add': self.add_command_handler,
            'remove': self.remove_command_handler,
            'list': self.list_command_handlers,
            'commit': self.db_commit,
            'add_global': self.add_global_command,
            'remove_global': self.remove_global_command,
            'get_globals': self.get_global_commands,
            'get': self.get_command_usage,
            'reset': self.reset_command_usage
        }

    def stop(self):
        self.db.close()

    def custom_roll_wrapper(self, cnt, dice):
        return lambda update, context: self.simple_roll(update, context, cnt, dice)

    # params: update and context
    def simple_roll(self, update: Update, context, cnt=1, rolls_dice=20, mod_act=None, mod_num=None):
        parsed = self.parse_simple_roll(update.message.text, cnt, rolls_dice, mod_act, mod_num, context.bot.name)
        command_text, comment, rolls_cnt, rolls_dice, mod_act, mod_num = parsed

        try:
            # get numbers and generate text
            rolls = [self.rnd(rolls_dice) for _ in range(rolls_cnt)]
            rolls_info = ' + '.join(str(r) for r in rolls)
            if rolls_cnt > 1:
                if cnt > 1:
                    rolls_sums = '(' + \
                                 ') + ('.join(str(sum(rolls[i * cnt:(i + 1) * cnt])) for i in range(rolls_cnt // cnt)) \
                                 + ')'
                else:
                    rolls_sums = '(' + ' + '.join(str(roll) for roll in rolls) + ')'
            else:
                rolls_sums = ''
            if mod_num is not None:
                if mod_num == 'h':
                    rolls_info = 'Max of (' + ', '.join(str(r) for r in rolls) + ') is ' + str(max(rolls))
                elif mod_num == 'l':
                    rolls_info = 'Min of (' + ', '.join(str(r) for r in rolls) + ') is ' + str(min(rolls))
                elif self.sanity_bound(mod_num, self.ONLY_DIGITS) == len(mod_num) > 0:
                    # PyCharm says it's ok. I hope so
                    rolls_info = rolls_sums + ' ' + mod_act + ' ' + mod_num + ' = ' + \
                                 str(eval(str(sum(rolls)) + mod_act + mod_num))
                else:
                    comment = mod_act + mod_num + comment
            text = self.get_user_name(update) + ': ' + comment + '\n' + rolls_info
            if rolls_cnt > 1 and mod_num is None:
                text += '\nSum: '
                if cnt != 1:
                    text += rolls_sums + ' = '
                text += str(sum(rolls))
            self.reply_to_message(update, text)
            self.db.increment_counted_roll(update.message.chat_id, update.message.from_user.id, command_text)
        except Exception as e:
            update.message.reply_text("{}: {}\n{}".format(self.get_user_name(update), update.message.text[3:],
                                                          ' + '.join(str(self.rnd(rolls_dice)) for _ in range(cnt))))
            raise e

    def equation_roll(self, update, _):
        s, rolls, rest = self.roll_processing(update.message.text[2:])
        r = self.calc(s)
        self.reply_to_message(update, self.get_user_name(update) + ': ' + rest + '\n' + s + '\n' +
                              (r[1] if r[0] is None else (' = ' + str(r[0]))))

    # just ping
    @staticmethod
    def ping(update, _):
        update.message.reply_text('Pong!')
        print('ping!')

    def add_global_command(self, update, context):
        if update.message.from_user.id == self.MASTER_ID:
            if update.message.text.count(' ') != 2:
                return self.reply_to_message(update, self.ss.USAGE(update) + "/add_global /roll 1d20")
            _, shortcut, roll = update.message.text.split()
            parsed = self.parse_simple_roll(shortcut + ' ' + roll, botname=context.bot.name)
            command_text, comment, rolls_cnt, rolls_dice, mod_act, mod_num = parsed
            roll = self.db.get_global_roll(shortcut)
            if roll is not None:
                self.reply_to_message(update, self.ss.ALREADY_HAS_COMMAND(update))
            self.db.set_global_roll(GlobalRoll(shortcut, rolls_cnt, rolls_dice, mod_act, mod_num))
            msg = self.ss.COMMAND_ADDED_SUCCESSFULLY(update) + "\n{} - {}d{}".format(shortcut, rolls_cnt, rolls_dice)
            if mod_act is not None:
                msg += mod_act + mod_num
            self.reply_to_message(update, msg)
        else:
            self.reply_to_message(update, self.ss.ACCESS_DENIED(update))

    def remove_global_command(self, update, _):
        if update.message.from_user.id == self.MASTER_ID:
            if update.message.text.count(' ') != 1:
                self.reply_to_message(update, self.ss.USAGE(update) + "/remove_global /roll")
                return
            shortcut = update.message.text.split()[1]
            res = self.db.remove_global_roll(GlobalRoll(shortcut, 1, 20))
            if res > 0:
                msg = self.ss.COMMAND_REMOVED_SUCCESSFULLY(update)
            else:
                msg = self.ss.UNKNOWN_COMMAND(update)
            self.reply_to_message(update, msg)
        else:
            self.reply_to_message(update, self.ss.ACCESS_DENIED(update))

    def get_global_commands(self, update, _):
        rolls = self.db.get_all_global_rolls()
        msg = self.ss.GLOBAL_COMMANDS(update)
        for roll in rolls:
            msg += "\n{} - {}d{}".format(roll.shortcut, roll.count, roll.dice)
            if roll.mod_act is not None:
                msg += roll.mod_act + roll.mod_num
        self.reply_to_message(update, msg)

    def get_command_usage(self, update, context):
        has_access, chat_id, target_id = self.is_user_has_stats_access(update, context)
        if has_access:
            rolls = self.db.filter_counted_roll(chat_id, user_id=target_id, command=None)
            if len(rolls) == 0:
                self.reply_to_message(update, self.ss.NO_USER_STATS(update))
            else:
                msg = self.ss.STATS(update)
                for roll in rolls:
                    msg += "\n{} - {} ".format(roll.command, roll.count) + self.ss.TIMES(update)
                self.reply_to_message(update, msg)

    def reset_command_usage(self, update, context):
        has_access, chat_id, target_id = self.is_user_has_stats_access(update, context)
        creator_id = self.get_chat_creator_id(context, chat_id)
        if has_access:
            cmds = update.message.text.split(' ')
            if len(cmds) == 1:
                return self.reply_to_message(update, self.ss.USAGE(update) + "/reset cmd")
            cmd = cmds[1]
            roll = self.db.get_counted_roll(chat_id, target_id, cmd)
            if roll is None:
                return self.reply_to_message(update, self.ss.NOTHING_RESET(update))
            count = roll.count
            if len(cmds) > 2:
                if creator_id == update.message.from_user.id:
                    roll.count = self.to_int(cmds[2], default=0, max_v=1000_000_000)
                    msg = self.ss.SET_NEW_VALUE(update).format(roll.count, count)
                else:
                    msg = self.ss.ACCESS_DENIED
            else:
                roll.count = 0
                msg = self.ss.RESET_OLD_VALUE(update) + str(count)
            self.db.set_counted_roll(roll)
            self.reply_to_message(update, msg)

    # get stats only to d20
    def get_stats(self, update, _):
        ts = update.message.text.split(' ', 2)
        if len(ts) > 1:
            dice = self.to_int(ts[1], default=20, max_v=1000000000)
        else:
            dice = 20
        stats = self.stats_to_dict()
        if dice in stats:
            overall = sum(stats[dice].values())
            msg = self.ss.STATS_UPTIME(update).format(
                (time.time() - self.start_time) / 3600) + self.ss.STATS_DICE(update).format(dice, overall)
            for i in range(1, dice + 1):
                if i in stats[dice]:
                    msg += "\n{0}: {1:.3f}".format(i, stats[dice][i] / overall * 100)
        else:
            msg = self.ss.NO_DICE_STATS(update)
        self.reply_to_message(update, msg)

    # get all stats
    def get_full_stats(self, update, _):
        msg = self.ss.STATS_UPTIME(update).format((time.time() - self.start_time) / 3600)
        stats = self.stats_to_dict()
        for key in sorted(stats.keys()):
            stat_sum = sum(stats[key])
            msg += self.ss.STATS_DICE(update).format(key, stat_sum)
            for i in range(1, key + 1):
                if i in stats[key]:
                    addition = "\n{}: {:.3f}".format(i, stats[key][i] / stat_sum * 100)
                    if len(msg) + len(addition) > 4000:
                        self.reply_to_message(update, msg)
                        msg = ''
                    msg += addition
        self.reply_to_message(update, msg)

    def help_handler(self, update, _):
        text = self.ss.HELP_MESSAGE(update)
        if update.message.from_user.id == self.MASTER_ID:
            text += self.ss.HELP_MASTER(update)
        self.reply_to_message(update, text)

    def add_command_handler(self, update, _):
        user_id = update.message.from_user.id
        if user_id not in self.pending_rolls:
            self.pending_rolls.append(user_id)
        self.reply_to_message(update, self.ss.ADD_COMMAND(update), is_markdown=True)

    def remove_command_handler(self, update, context):
        user_id = update.message.from_user.id
        ts = update.message.text.split()
        if len(ts) == 2:
            cmd = ts[1].replace(context.bot.name, '').lstrip('/')
            if len(cmd) > 0:
                custom_roll = self.db.get_custom_roll(user_id, cmd)
                if custom_roll is not None:
                    self.db.remove_custom_roll(custom_roll)
                    self.reply_to_message(update, self.ss.DELETED_COMMAND(update).format(cmd))
                else:
                    self.reply_to_message(update, self.ss.UNKNOWN_COMMAND(update))
        else:
            self.reply_to_message(update, self.ss.USAGE(update) + "`/remove your_cmd`", is_markdown=True)

    def list_command_handlers(self, update, _):
        user_id = update.message.from_user.id
        custom_rolls = self.db.filter_custom_roll(user_id, shortcut=None)
        if len(custom_rolls) == 0:
            self.reply_to_message(update, self.ss.NO_CUSTOM(update))
        else:
            msg = self.ss.YOUR_COMMANDS(update)
            for custom_roll in custom_rolls:
                msg += "\n/{} - {}d{}".format(custom_roll.shortcut, custom_roll.count, custom_roll.dice)
                if custom_roll.mod_act is not None:
                    msg += custom_roll.mod_act + custom_roll.mod_num
            if user_id in self.pending_rolls:
                msg += self.ss.CUSTOM_PENDING(update)
            self.reply_to_message(update, msg)

    def all_commands_handler(self, update, context):
        if update.message.text is None or len(update.message.text) == 0 or update.message.text[0] != '/':
            return  # Not a command
        user_id = update.message.from_user.id
        cmd = update.message.text.split()[0][1:].replace(context.bot.name, '').lstrip('/')
        roll = self.db.get_global_roll('/' + cmd)
        if roll is not None:
            return self.simple_roll(update, context, roll.count, roll.dice, roll.mod_act, roll.mod_num)
        if user_id in self.pending_rolls:
            parsed = self.parse_simple_roll(update.message.text, botname=context.bot.name)
            command_text, comment, rolls_cnt, rolls_dice, mod_act, mod_num = parsed
            if ' ' in command_text:
                self.db.set_custom_roll(CustomRoll(user_id, cmd, rolls_cnt, rolls_dice, mod_act, mod_num))
                self.pending_rolls.remove(user_id)
                msg = self.ss.COMMAND_ADDED_SUCCESSFULLY(update) + "\n{} - {}d{}".format(cmd, rolls_cnt, rolls_dice)
                if mod_act is not None:
                    msg += mod_act + mod_num
                self.reply_to_message(update, msg)
            else:
                self.reply_to_message(update, self.ss.NEED_ARGUMENTS(update), is_markdown=True)
        else:
            custom_roll = self.db.get_custom_roll(user_id, cmd)
            if custom_roll is not None:
                self.simple_roll(update, context, custom_roll.count, custom_roll.dice,
                                 custom_roll.mod_act, custom_roll.mod_num)

    def db_commit(self, update, _):
        if update.message.from_user.id == self.MASTER_ID:
            self.db.commit()
            update.message.reply_text(self.ss.OK(update))

    # log all errors
    def error_handler(self, update: Update, context: CallbackContext):
        logging.error('Error: {} ({} {}) caused.by {}'.format(context, type(context.error), context.error, update))
        print("Error: " + str(context.error))
        if update is not None and update.message is not None:
            update.message.reply_text("Error")
            context.bot.send_message(chat_id=self.MASTER_ID, text="Error: {} {} for message {}".format(
                str(type(context.error))[:1000], str(context.error)[:2000], str(update.message.text)[:1000]))


# start
def init(token):
    if not os.path.exists('data'):
        os.makedirs('data')
    rollbot = Rollbot()

    updater = Updater(token=token, use_context=True)
    # adding handlers
    for command, func in rollbot.global_commands.items():
        updater.dispatcher.add_handler(CommandHandler(command, func))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, rollbot.all_commands_handler))
    updater.dispatcher.add_error_handler(rollbot.error_handler)

    updater.start_polling()
    updater.idle()
    print("Stopping")
    rollbot.stop()


if __name__ == '__main__':
    print("Started", time.time())
    init(rollbot_secret_token.token)
