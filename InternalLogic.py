import os
import random
from typing import Tuple, Dict, List


class InternalLogic:
    """
        Класс внутренней логики бота
        Команды обрабатываются по нотации костей:
        https://en.wikipedia.org/wiki/Dice_notation
    """
    ONLY_DIGITS = ''.join(str(i) for i in range(10))
    DICE_NOTATION = ONLY_DIGITS + 'dD '

    def __init__(self, master_id: int, rolls: Dict[str, Tuple[int, int]]):
        """
            Создание экземпляра класса
            :param master_id - id аккаунта с расширенным доступом к боту
            :param rolls - список роллов по умолчанию в виде словаря "команда: (количество бросков, количество граней)"
        """
        self.stats: Dict[int, Dict[int, int]] = {}
        self.master_id = master_id
        self.rolls = rolls

    def increment_stat(self, dice: int, result: int):
        """
            Увеличить счетчик результатов бросков на один
            :param dice - количество граней броска
            :param result - результат броска
        """
        if dice not in self.stats:
            self.stats[dice] = {}
        if result not in self.stats[dice]:
            self.stats[dice][result] = 1
        else:
            self.stats[dice][result] += 1

    def rnd(self, dice: int) -> int:
        """
        сгенерировать рандомное число от 1 до :param dice и записать в статистику
        :return: полученное число
        """
        dice = abs(dice)  # remove negative values
        if dice == 0 or dice > 1000000:
            dice = 20  # remove incorrect
        bin_len = len(bin(dice)) - 2

        # 1000 попыток для генерации чего-то похожего на криптографический рандом
        num_cnt, mask = bin_len // 8, (1 << (bin_len % 8)) - 1
        for _ in range(1000):
            nums = list(os.urandom(num_cnt + 1))
            nums[0] &= mask
            n = 0
            for i in nums:
                n = (n << 8) + i
            if n != 0 and n <= dice:
                res = n
                break
        else:
            # резервный вариант
            res = random.randrange(dice) + 1

        self.increment_stat(dice, res)
        return res

    # return: [command_text, comment, count, dice]
    @staticmethod
    def parse_simple_roll(text: str, default_count: int = 1, default_dice: int = 20) -> Tuple[int, int]:
        """
        Распарсить команду боту из команды формата "/r 1d20", получив пару (количество бросков, количество граней)
        :param text: текст команды
        :param default_count: если не указано в команде, столько бросков будет возвращено
        :param default_dice: если не указано в команде, столько граней будет возвращено
        :return: два (количество бросков, количество граней) параметра броска
        """
        # separating comment and roll params
        ts = text.split(' ', 1)
        rolls_dice, rolls_cnt = default_dice, default_count
        if len(ts) > 1:  # not only `r`
            # cut out comment
            split_pos = InternalLogic.sanity_bound(ts[1], InternalLogic.DICE_NOTATION)
            command = ts[1][:split_pos].strip().lower()

            command = command.split('d')
            rolls_cnt = InternalLogic.to_int(command[0], 1)
            if len(command) > 1:
                rolls_dice = InternalLogic.to_int(command[1], 20)
        return rolls_cnt, rolls_dice

    # -> (message_text, command_text)
    def process_roll(self, text: str, default_count: int, default_dice: int) -> str:
        """
        Обработать сообщение с броском костей
        :param text: текст команды вида "/r 1d20" (1d20 - см википедию)
        :param default_count: если не указано в команде, столько бросков будет возвращено
        :param default_dice: если не указано в команде, столько граней будет возвращено
        :return: сообщение, которое вернется пользователю
        """
        rolls_cnt, default_dice = self.parse_simple_roll(text, default_count, default_dice)

        # get numbers and generate text
        rolls = [self.rnd(default_dice) for _ in range(rolls_cnt)]
        text = ' + '.join(str(r) for r in rolls)
        if rolls_cnt > 1:
            text += '\nSum: ' + str(sum(rolls))
        return text

    def process_add_global(self, text: str, user_id: int) -> str:
        """
        Обработать сообщение с добавлением глобальной команды
            Это может сделать только пользователь с расширенными привилегиями
        :param text: текст команды вида "/add_global /roll 1d20", где /roll - новая глобальная команда
            1d20 - значение ролла по умолчанию
        :param user_id: id пользователя, который отправил сообщение
        :return: сообщение, которое вернется пользователю
        """
        if user_id != self.master_id:
            return "Access denied"
        else:
            if text.count(' ') != 2:
                return "Usage: /add_global /roll 1d20"
            _, shortcut, roll = text.split()
            rolls_cnt, rolls_dice = self.parse_simple_roll(shortcut + ' ' + roll)

            self.rolls[shortcut] = (rolls_cnt, rolls_dice)
            return "Command added successfully!\n{} - {}d{}".format(shortcut, rolls_cnt, rolls_dice)

    def process_remove_global(self, text: str, user_id: int) -> str:
        """
        Обработать сообщение с удалением глобальной команды
            Это может сделать только пользователь с расширенными привилегиями
        :param text: текст команды вида "/remove_global /roll", где /roll - существующая глобальная команда
        :param user_id: id пользователя, который отправил сообщение
        :return: сообщение, которое вернется пользователю
        """
        if user_id != self.master_id:
            return "Access denied"
        else:
            if text.count(' ') != 1:
                return "Usage: /remove_global /roll"
            shortcut = text.split()[1]
            if shortcut in self.rolls:
                del self.rolls[shortcut]
            return "Command removed successfully!"

    def process_stats(self) -> List[str]:
        """
        Вернуть статистику по броскам, сгруппировав в сообщения по 4000 символов
        :return: список получившихся значений
        """
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

    @staticmethod
    def sanity_bound(string: str, allowed: str) -> int:
        """
        Просмотреть строку :param string: и вернуть индекс первого символа, который не содержится в :param allowed:
        :return: индекс первого "лишнего" символа
        """
        for i in range(len(string)):
            if string[i] not in allowed:
                return i
        return len(string)

    @staticmethod
    def to_int(data: str, default: int) -> int:
        """
        Преобразовать строку :param data: в число. В случае ошибки вернуть :param default:
        :return: число из строки либо дефолтное значение
        """
        try:
            return int(data)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def reply_to_message(update, text: str):
        """
        Ответить на сообщение, которое пришло в update, обрезав по 4092 символа
            по возможности обрезает на переводе строк
        :param update: метод update.message.reply_text вызывается с параметром - обрезанная строка
        :param text: сообщение, которое отправляется
        """
        while len(text) > 4092:
            last = text[:4096].rfind('\n')
            if last > 0:
                last = 4092
            update.message.reply_text(text[:last])
            text = text[last:]
        update.message.reply_text(text)

    @staticmethod
    def get_user_name(update) -> str:
        """
        Если update.message.from_user.name задано, то вернуть его
        Иначе update.message.from_user.firstname
        :param update: ивент нового сообщения, из которого беруются поля пользователя
        :return: юзернейм пользователя. Если его нет - имя
        """
        return str(update.message.from_user.name) if update.message.from_user.name is not None \
            else str(update.message.from_user.firstname)
