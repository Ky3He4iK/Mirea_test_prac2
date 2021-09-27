import os
import random


class InternalLogic:
    ONLY_DIGITS = ''.join(str(i) for i in range(10))
    DICE_NOTATION = ONLY_DIGITS + 'd '

    def __init__(self, master_id: int, rolls: dict):
        self.stats = {}
        self.master_id = master_id
        self.rolls = rolls

    def increment_stat(self, dice, result):
        if dice not in self.stats:
            self.stats[dice] = {}
        if result not in self.stats[dice]:
            self.stats[dice][result] = 1
        else:
            self.stats[dice][result] += 1

    # returns an integer from 1 to dice inclusively and add result to stats
    def rnd(self, dice: int) -> int:
        dice = abs(dice)  # remove negative values
        if dice == 0 or dice > 1000000:
            dice = 20  # remove incorrect
        res = self.get_random_num(dice)
        self.increment_stat(dice, res)
        return res

    # return: [command_text, comment, count, dice]
    @staticmethod
    def parse_simple_roll(text, default_count=1, default_dice=20):

        # separating comment and roll params
        ts = text.split(' ', 1)
        comment = ''
        rolls_dice, rolls_cnt = default_dice, default_count
        shortcut = ts[0][:ts[0].find('@')] if '@' in ts[0] else ts[0]
        if len(ts) > 1:  # not only `r`
            # cut out comment
            split_pos = InternalLogic.sanity_bound(ts[1], InternalLogic.DICE_NOTATION)
            command, comment = ts[1][:split_pos].strip().lower(), ts[1][split_pos:].strip()

            command = command.split('d')
            rolls_cnt = InternalLogic.to_int(command[0])
            if len(command) > 1:
                rolls_dice = InternalLogic.to_int(command[1])
        if rolls_dice == default_dice and rolls_cnt == default_count:
            command_text = shortcut
        else:
            command_text = shortcut + "{}d{}".format(rolls_cnt, rolls_dice)
        return [command_text, comment, rolls_cnt, rolls_dice]

    # -> (message_text, command_text)
    def process_roll(self, text: str, cnt: int, rolls_dice: int) -> str:
        command_text, comment, rolls_cnt, rolls_dice = self.parse_simple_roll(text, cnt, rolls_dice)

        # get numbers and generate text
        rolls = [self.rnd(rolls_dice) for _ in range(rolls_cnt)]
        rolls_info = ' + '.join(str(r) for r in rolls)
        text = comment + '\n' + rolls_info
        if rolls_cnt > 1:
            text += '\nSum: ' + str(sum(rolls))
        return text

    def process_add_global(self, text: str, user_id: int) -> str:
        if user_id != self.master_id:
            return "Access denied"
        else:
            if text.count(' ') != 2:
                return "Usage: /add_global /roll 1d20"
            _, shortcut, roll = text.split()
            command_text, comment, rolls_cnt, rolls_dice = self.parse_simple_roll(shortcut + ' ' + roll)

            self.rolls[shortcut] = (rolls_cnt, rolls_dice)
            return "Command added successfully!\n{} - {}d{}".format(shortcut, rolls_cnt, rolls_dice)

    def process_remove_global(self, text: str, user_id: int) -> str:
        if user_id != self.master_id:
            return "Access denied"
        else:
            if text.count(' ') != 1:
                return "Usage: /remove_global /roll"
            shortcut = text.split()[1]
            if shortcut in self.rolls:
                del self.rolls[shortcut]
            return "Command removed successfully!"

    def process_stats(self):
        msgs = ["Stats for this bot:\n"]
        for key in sorted(self.stats.keys()):
            stat_sum = sum(self.stats[key])
            msgs[-1] += "\nd{} stats (%): from {} rolls".format(key, stat_sum)
            for i in range(1, key + 1):
                if i in self.stats[key]:
                    addition = "\n{}: {:.3f}".format(i, self.stats[key][i] / stat_sum * 100)
                    if len(msgs[-1]) + len(addition) > 4000:
                        msgs.append('')
                    msgs[-1] += addition
        return msgs

    # get creator of chat with chat_id
    @staticmethod
    def get_chat_creator_id(context, chat_id):
        return list(filter(lambda a: a.status == a.CREATOR, context.bot.getChatAdministrators(chat_id)))[0].user.id

    # get number in [1, max_val] using "true" random
    @staticmethod
    def get_random_num(max_val: int) -> int:
        bin_len = len(bin(max_val)) - 2
        num_cnt, mask = bin_len // 8, (1 << (bin_len % 8)) - 1
        for _ in range(1000):  # 1k tries for "true" cryptographic random
            nums = list(os.urandom(num_cnt + 1))
            nums[0] &= mask
            n = 0
            for i in nums:
                n = (n << 8) + i
            if n != 0 and n <= max_val:
                return n
        # fallback - use default python random
        return random.randrange(max_val) + 1

    @staticmethod
    def get_user_name(update):
        return str(update.message.from_user.name) if update.message.from_user.name is not None \
            else str(update.message.from_user.firstname)

    # checks for sanity string. Returns first not sane index
    @staticmethod
    def sanity_bound(string, allowed):
        for i in range(len(string)):
            if string[i] not in allowed:
                return i
        return len(string)

    @staticmethod
    def to_int(data):
        try:
            return int(data)
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def reply_to_message(update, text: str):
        while len(text) > 4095:
            last = text[:4096].rfind('\n')
            if last < 1000:
                last = 4092
            update.message.reply_text(text[:last])
            text = text[last:]
        update.message.reply_text(text)
