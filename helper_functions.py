import random
import os
from database import Database
from StringsStorage import StringsStorage


class Helper:
    MASTER_ID = 351693351
    ONLY_DIGITS = ''.join(str(i) for i in range(10))
    DICE_NOTATION = ONLY_DIGITS + 'dD%+-*/hHlL '

    def __init__(self):
        self.db = Database()
        self.ss = StringsStorage()

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

    # returns an integer from 1 to dice inclusively and add result to stats
    def rnd(self, dice: int) -> int:
        dice = abs(dice)  # remove negative values
        if dice == 0 or dice > 1000000:
            dice = 20  # remove incorrect
        res = self.get_random_num(dice)
        self.db.increment_stat(dice, res)
        return res

    @staticmethod
    def reply_to_message(update, text: str, is_markdown=False):
        while len(text) > 4095:
            last = text[:4096].rfind('\n')
            if last == -1:
                update.message.reply_text(text[:4092] + '...')
                text = text[4092:]
            else:
                update.message.reply_text(text[:last])
                text = text[last + 1:]
        update.message.reply_text(text, parse_mode=("MarkdownV2" if is_markdown else None))

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

    # converts string to integer bounded to [min_v, max_v]. Returns default on fault
    @staticmethod
    def to_int(data, *_, default, max_v, min_v=1):
        try:
            return min(max(int(data), min_v), max_v)
        except (TypeError, ValueError):
            return default

    # s - string with some expression and dices in format `5d9`
    #   (one or both arguments may be missing. Default value is 1d20; `d%` is `d100`)
    # random_generator - function that returns value from 1 to given argument inclusively
    def roll_processing(self, s):
        i = Helper.sanity_bound(s, Helper.ONLY_DIGITS + 'd% +-*/()')
        rest, s = s[i:], s[:i].strip()
        if len(s) == 0:
            s = 'd'
        i, rolls = 0, []
        while i < len(s):
            if s[i] == 'd':  # found dice
                j = i - 1  # j is left border for dice count
                while j >= 0 and s[j].isnumeric():
                    j -= 1
                cnt = Helper.to_int(s[j + 1:i], max_v=1000, default=1)
                k = i + 1  # k is right border for dice max value
                if i + 1 < len(s) and s[i + 1] == '%':
                    mod = 100
                else:
                    while k < len(s) and s[k].isnumeric():
                        k += 1
                    mod = Helper.to_int(s[i + 1:k], max_v=1000000, default=20)
                    k -= 1
                rolls += [str(self.rnd(mod)) for _ in range(cnt)]
                added = '(' + '+'.join(rolls[len(rolls) - cnt:]) + ')'
                s = s[:j + 1] + added + s[k + 1:]
                i = j + len(added)
            i += 1
        return s, rolls, rest

    @staticmethod
    def calc(expression):
        # check item type
        def is_int(item):
            return type(item) == int

        def is_str(item):
            return type(item) == str

        # First part gets string and deletes whitespace
        # Then it creates the list and adds each individual character to the list
        expr_list = [int(ch) if ord('0') <= ord(ch) <= ord('9') else ch for ch in expression.replace(' ', '')]
        pos = 1
        # combine numbers together and check expression
        while pos < len(expr_list):
            if is_int(expr_list[pos - 1]) and expr_list[pos] == "(":
                expr_list.insert(pos, '*')  # insert missing asterisk
            elif is_int(expr_list[pos - 1]) and is_int(expr_list[pos]):
                expr_list[pos - 1] = expr_list[pos - 1] * 10 + expr_list[pos]
                del expr_list[pos]
            else:
                pos += 1

        # If the length of the list is 1, there is only 1 number, meaning an answer has been reached.
        try:
            while len(expr_list) != 1:
                changed = False  # if the are no changes then something is wrong. Preferably expression
                # remove parentheses around a single item
                pos = 2
                while pos < len(expr_list):
                    if expr_list[pos - 2] == "(" and expr_list[pos] == ")":
                        expr_list = expr_list[:pos - 2] + [expr_list[pos - 1]] + expr_list[pos + 1:]
                        changed = True
                    pos += 1
                # */
                pos = 1
                while pos < len(expr_list) - 1:
                    if is_str(expr_list[pos]) and is_int(expr_list[pos + 1]) and is_int(expr_list[pos - 1]) \
                            and expr_list[pos] in "*/":
                        if expr_list[pos] == '*':
                            expr_list[pos - 1] *= expr_list[pos + 1]
                        elif expr_list[pos] == '/':
                            expr_list[pos - 1] //= expr_list[pos + 1]
                        expr_list = expr_list[:pos] + expr_list[pos + 2:]
                        changed = True
                    else:
                        pos += 1
                # +-
                pos = 1
                while pos < len(expr_list) - 1:
                    if is_str(expr_list[pos]) and is_int(expr_list[pos + 1]) and is_int(expr_list[pos - 1]) \
                            and expr_list[pos] in "+-":
                        if expr_list[pos] == '+':
                            expr_list[pos - 1] += expr_list[pos + 1]
                        elif expr_list[pos] == '-':
                            expr_list[pos - 1] -= expr_list[pos + 1]
                        expr_list = expr_list[:pos] + expr_list[pos + 2:]
                        changed = True
                    else:
                        pos += 1
                if not changed:
                    return None, "Invalid expression"
            return int(expr_list[0]), ""
        except ZeroDivisionError:
            return None, "Division by zero"

    # return: [command_text, comment, count, dice, mod_act, mod_num]
    @staticmethod
    def parse_simple_roll(text, default_count=1, default_dice=20, default_mod_act=None, default_mod_num=None,
                          botname='@dice_cheating_bot'):
        def eq(a, b) -> bool:
            if b is None:
                return a is None
            return a == b

        # separating comment and roll params
        ts = text.split(' ', 1)
        comment = ''
        rolls_dice, rolls_cnt = default_dice, default_count
        mod_act, mod_num = default_mod_act, default_mod_num
        command_shortcut = ts[0].replace(botname, '')
        if len(ts) > 1:  # not only `r`
            # cut out comment
            split_pos = Helper.sanity_bound(ts[1], Helper.DICE_NOTATION)
            command, comment = ts[1][:split_pos].strip().lower(), ts[1][split_pos:].strip()
            # cut out appendix (+6, *4, etc.)
            for i in range(len(command)):
                if command[i] in '+-*/':
                    mod_act = command[i]
                    if mod_act == '/':
                        mod_act = '//'
                    command, mod_num = [s.strip() for s in command.split(command[i], 1)]
                    split_pos = Helper.sanity_bound(mod_num, Helper.ONLY_DIGITS)  # remove other actions
                    mod_num, comment = mod_num[:split_pos], mod_num[split_pos:] + comment
                    break
                elif command[i] in 'hl':
                    mod_num = command[i]
                    command = command[:i]
            command = command.split('d')
            rolls_cnt = Helper.to_int(command[0], default=1, max_v=1000) * default_count
            if len(command) > 1:
                rolls_dice = Helper.to_int(command[1], default=None, max_v=1000000)
        if rolls_dice == default_dice and rolls_cnt == default_count and eq(mod_act, default_mod_act) and \
                eq(mod_num, default_mod_num):
            command_text = command_shortcut
        else:
            command_text = command_shortcut + "{}d{}".format(rolls_cnt, rolls_dice)
            if mod_act is not None:
                command_text += mod_act + mod_num
            elif mod_num is not None:
                command_text += mod_num
        return [command_text, comment, rolls_cnt, rolls_dice, mod_act, mod_num]

    def is_user_has_stats_access(self, update, context) -> (bool, int, int):
        # has_access, chat_id, user_id
        chat_id, user_id = update.message.chat_id, update.message.from_user.id
        is_admin = user_id == Helper.MASTER_ID or (chat_id != user_id and
                                                   Helper.get_chat_creator_id(context, chat_id) == user_id)
        if update.message.reply_to_message is not None:
            target_id = update.message.reply_to_message.from_user.id
        else:
            target_id = user_id
        if not is_admin and user_id != target_id:
            Helper.reply_to_message(update, self.ss.CHAT_CREATOR_ONLY(update))
            return False, chat_id, target_id
        return True, chat_id, target_id

    def stats_to_dict(self):
        stats = {}
        for stat in self.db.get_all_stats():
            if stat.dice not in stats:
                stats[stat.dice] = {}
            stats[stat.dice][stat.result] = stat.count
        return stats
