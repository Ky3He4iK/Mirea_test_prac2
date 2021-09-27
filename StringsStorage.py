from dataclasses import dataclass


@dataclass
class String:
    ru_str: str
    en_str: str

    def __call__(self, update):
        if update.message.from_user.language_code == "ru":
            return self.ru_str
        return self.en_str


class StringsStorage:
    CHAT_CREATOR_ONLY = String("Только создатель чата имеет доступ", "Only creator of this chat has access")
    USAGE = String("Использование: ", "Usage: ")
    ALREADY_HAS_COMMAND = String("Уже есть такая комманда!", "Already has this command!")
    COMMAND_ADDED_SUCCESSFULLY = String("комманда добавлена успешно!", "Command added successfully!")
    COMMAND_REMOVED_SUCCESSFULLY = String("комманда удалена успешно!", "Command removed successfully!")
    ACCESS_DENIED = String("Доступ запрещен", "Access denied")
    UNKNOWN_COMMAND = String("Неизвестная комманда", "Unknown command")
    GLOBAL_COMMANDS = String("Глобальные комманды:", "Global commands:")
    NO_USER_STATS = String("Нет статистики для этого пользователя", "No statistics for this user")
    STATS = String("Статистика:", "Statistics:")
    TIMES = String("раз", "times")
    NOTHING_RESET = String("Нечего сбрасывать", "Nothing to reset")
    RESET_OLD_VALUE = String("Сброшено. Старое значение: ", "Reset. Old value: ")
    SET_NEW_VALUE = String("Установлено новое значение. Теперь {} вместо {}", "Set a new value. Now {} instead of {}")
    NO_DICE_STATS = String("Нет информации для этой кости", "No information for this dice!")
    STATS_UPTIME = String("Статистика этого бота:\nРаботает: {:.2f} часов", "Stats for this bot:\nUptime: {} hours")
    STATS_DICE = String("\nСтатистика для d{} (%): из {} бросков", "\nd{} stats (%): from {} rolls")
    ADD_COMMAND = String("Окей, теперь отправь комманду и что она обозначает\\. Например: `/2d6_1 2d6 + 1`",
                         "Ok, now send me command and what it will stands for\\. For example: `/2d6_1 2d6 + 1`")
    DELETED_COMMAND = String("комманда {} удалена успешно!", "Deleted {} successfully!")
    NO_CUSTOM = String("У тебя нет собственных комманд", "You have no custom commands")
    YOUR_COMMANDS = String("Твои комманды:", "Your commands:")
    CUSTOM_PENDING = String("Ожидается добавление собаственной комманды", "Pending custom command to add")
    NEED_ARGUMENTS = String("Нужны аргументы для комманды\\. Например: `/2d6_1 2d6+1`",
                            "Need arguments for command\\. For example: `/2d6_1 2d6+1`")
    OK = String("Ок", "OK")
    HELP_MESSAGE = String("""
/r - кинуть кости. Можно указать количество костей и количество граней на каждой кости, например /r 3d6 - куб на статы. Можно еще указать модификатор броска, например /r +3
Указывается либо количество костей (число), либо количество граней (d + число), либо модификатор (знак модификатора - один из "-+*/" + число), либо любая их комбинация, например /r 5d8*3
По умолчанию кидается 1d20, также есть аналогичные комманды, с разными бросками по умолчанию:
/c /c1 /c2 /c3 /c4 /c5 /c6 - 3d6
/s - 1d11
/p - 1d100
Полный список доступных бросков можно получить по комманде /get_globals  

Если кому-то этих комманд недостаточно, то можно добавить свои персональные комманды: /add первым сообщением и комманда вторым. Например: 
/add
/2d6_1 2d6+1
/remove cmd - удалить cmd из списка персональных комманд
/list - список персональных комманд

Еще можно кидать составные броски в виде уравнения - /d *уравнение*
Например: /d (1d20 + d30)/2

Бот также собирает статистику:
/stats N - получить статистику для роллов дайса N, по умолчанию 20
/statsall - получить статистику всех бросков
/get (в ответ на чье-нибудь сообщение) - узнать, сколько раз человек кидал какие роллы в этом чате
/reset /c (в ответ на чье-нибудь сообщение) - сбросить статистику человека для комманды /c
Если надо установить определенное значение статистики, то указать после комманды, например /reset /c 42 (только для создателя чата)
Чужую статистику смотреть и сбрасывать можно только создателю чата (и создателю бота, по блату)
""", """
/r - Throw dices. You can specify dice count and number of faces of each dice, for example /r 3d6 - cube for statistics check. You can also specify throw modifier, for example /r +3
Specify either the number of bones (number), or the number of faces (d + number), or a modifier (modifier sign - one of "-+*/" + number), or any combination of them, for example /r 5d8*3
The default roll is 1d20, there are also similar commands, with different default rolls:
/c /c1 /c2 /c3 /c4 /c5 /c6 - 3d6
/s - 1d11
/p - 1d100
A complete list of available throws can be obtained by the command /get_globals

If these commands are not enough, then you can add your personal commands: /add with the first message and the command with the second. For example:
/add
/2d6_1 2d6 + 1
/remove cmd - remove cmd from the list of personal commands
/list - list of personal commands

You can also throw compound throws in the form of an equation - /d * equation *
For example: /d (1d20 + d30)/2

The bot also collects statistics:
/stats N - get statistics for N dice rolls, by default 20
/statsall - get statistics of all throws
/get (in response to someone's message) - find out how many times a person has thrown which rolls in this chat
/reset /c (in response to someone's message) - reset the person's statistics for the /c command
If you need to set a specific value of statistics, then specify after the command, for example /reset /c 42 (chat creator only) 
Someone else's statistics can only be viewed and reset by the creator of the chat""")
    HELP_MASTER = String("""
\n/add_globall /roll 1d20 - добавить новую глобальную комманду
\n/remove_globall /roll - удалить глобальную комманду
""", """
\n/add_globall /roll 1d20 - add a new global roll
\n/remove_globall /roll - remove global roll
""")
