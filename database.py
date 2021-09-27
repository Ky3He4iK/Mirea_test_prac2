import sqlite3
from dataclasses import dataclass
from typing import Optional, Union, Iterable, List
import logging
import os
import json


@dataclass
class Stat:
    dice: int
    result: int
    count: int


@dataclass
class CustomRoll:
    user_id: int
    shortcut: str
    count: int
    dice: int
    mod_act: Optional[str] = None
    mod_num: Optional[str] = None


@dataclass
class GlobalRoll:
    shortcut: str
    count: int
    dice: int
    mod_act: Optional[str] = None
    mod_num: Optional[str] = None


@dataclass
class CountedRoll:
    chat_id: int
    user_id: int
    command: str
    count: int


#  Сокращение некоторых внутренних типов
STR_OR_INT = Union[str, int]
STR_OR_ITER = Union[str, Iterable[str]]
STR_OR_INT_OR_ITER = Union[STR_OR_INT, Iterable[STR_OR_INT]]


class ContentTypes:
    STAT = "Stat"
    CUSTOM_ROLL = "CustomRoll"
    GLOBAL_ROLL = "GlobalRoll"
    COUNTED_ROLL = "CountedRoll"


class Database:
    # название класса: [[столбцы, которые являются фильтрами], [столбцы, значение в которых может меняться],
    #                   "название таблицы"]
    # все столбцы в таблице должны быть указаны
    CONTENT_INFO = {
        ContentTypes.STAT: [
            ["dice", "result"],
            ["count"],
            "stats"
        ],
        ContentTypes.CUSTOM_ROLL: [
            ["user_id", "shortcut"],
            ["count", "dice", "mod_act", "mod_num"],
            "custom_rolls"
        ],
        ContentTypes.GLOBAL_ROLL: [
            ["shortcut"],
            ["count", "dice", "mod_act", "mod_num"],
            "global_rolls"
        ],
        ContentTypes.COUNTED_ROLL: [
            ["chat_id", "user_id", "command"],
            ["count"],
            "counted_rolls"
        ],
    }

    def __init__(self):
        self._base = sqlite3.connect("data/rollbot.db", check_same_thread=False)
        self._base.isolation_level = None

    def close(self):
        self._base.close()

    def commit(self):
        self._base.commit()

    # stat
    def get_stat(self, dice: int, result: int) -> Optional[Stat]:
        stat = self.get(Stat(dice, result, 0), ContentTypes.STAT)
        if stat:
            return Stat(*stat)
        return None

    def filter_stat(self, dice: Optional[int], result: Optional[int]) -> List[Stat]:
        stats = self.filter(Stat(dice, result, 0), ContentTypes.STAT)
        return [Stat(*stat) for stat in stats]

    def set_stat(self, stat: Stat):
        return self.set(stat, ContentTypes.STAT)

    def get_all_stats(self):
        return [Stat(*row) for row in self.get_all(ContentTypes.STAT)]

    def increment_stat(self, dice: int, result: int):
        stat = self.get_stat(dice, result)
        if stat is None:
            stat = Stat(dice, result, 1)
        else:
            stat.count += 1
        return self.set(stat, ContentTypes.STAT)

    def remove_stat(self, stat: Stat):
        return self.remove(stat, ContentTypes.STAT)

    # custom roll
    def get_custom_roll(self, user_id: int, shortcut: str) -> Optional[CustomRoll]:
        custom_roll = self.get(CustomRoll(user_id, shortcut, 0, 0, None, None), ContentTypes.CUSTOM_ROLL)
        if custom_roll:
            return CustomRoll(*custom_roll)
        return None

    def filter_custom_roll(self, user_id: Optional[int], shortcut: Optional[str]) -> List[CustomRoll]:
        custom_rolls = self.filter(CustomRoll(user_id, shortcut, 0, 0, None, None), ContentTypes.CUSTOM_ROLL)
        return [CustomRoll(*custom_roll) for custom_roll in custom_rolls]

    def set_custom_roll(self, custom_roll: CustomRoll):
        return self.set(custom_roll, ContentTypes.CUSTOM_ROLL)

    def get_all_custom_rolls(self):
        return [CustomRoll(*row) for row in self.get_all(ContentTypes.CUSTOM_ROLL)]

    def remove_custom_roll(self, custom_roll: CustomRoll):
        return self.remove(custom_roll, ContentTypes.CUSTOM_ROLL)

    # global roll
    def get_global_roll(self, shortcut: str) -> Optional[GlobalRoll]:
        global_roll = self.get(GlobalRoll(shortcut, 0, 0, None, None), ContentTypes.GLOBAL_ROLL)
        if global_roll:
            return GlobalRoll(*global_roll)
        return None

    def filter_global_roll(self, shortcut: Optional[str]) -> List[GlobalRoll]:
        global_rolls = self.filter(GlobalRoll(shortcut, 0, 0, None, None), ContentTypes.GLOBAL_ROLL)
        return [GlobalRoll(*roll) for roll in global_rolls]

    def set_global_roll(self, global_roll: GlobalRoll):
        return self.set(global_roll, ContentTypes.GLOBAL_ROLL)

    def get_all_global_rolls(self):
        return [GlobalRoll(*row) for row in self.get_all(ContentTypes.GLOBAL_ROLL)]

    def remove_global_roll(self, global_roll: GlobalRoll):
        return self.remove(global_roll, ContentTypes.GLOBAL_ROLL)

    # counted roll
    def get_counted_roll(self, chat_id: int, user_id: int, command: str) -> Optional[CountedRoll]:
        counted_roll = self.get(CountedRoll(chat_id, user_id, command, 0), ContentTypes.COUNTED_ROLL)
        if counted_roll:
            return CountedRoll(*counted_roll)
        return None

    def filter_counted_roll(self, chat_id: Optional[int], user_id: Optional[int], command: Optional[str]) \
            -> List[CountedRoll]:
        counted_rolls = self.filter(CountedRoll(chat_id, user_id, command, 0), ContentTypes.COUNTED_ROLL)
        return [CountedRoll(*roll) for roll in counted_rolls]

    def set_counted_roll(self, counted_roll: CountedRoll):
        return self.set(counted_roll, ContentTypes.COUNTED_ROLL)

    def get_all_counted_rolls(self):
        return [CountedRoll(*row) for row in self.get_all(ContentTypes.COUNTED_ROLL)]

    def increment_counted_roll(self, chat_id: int, user_id: int, command: str):
        counted_roll = self.get_counted_roll(chat_id, user_id, command)
        if counted_roll is None:
            counted_roll = CountedRoll(chat_id, user_id, command, 1)
        else:
            counted_roll.count += 1
        return self.set(counted_roll, ContentTypes.COUNTED_ROLL)

    def remove_counted_roll(self, counted_roll: CountedRoll):
        return self.remove(counted_roll, ContentTypes.COUNTED_ROLL)

    # internal universal methods
    def set(self, obj, classname: str):
        if self.contains(obj, classname):
            return self.update(obj, classname)
        return self.insert(obj, classname)

    def insert(self, obj, classname: str):
        info = self.CONTENT_INFO[classname]
        columns = info[0] + info[1]
        fields = [getattr(obj, c) for c in columns]
        return self._insert(info[2], columns, fields)

    def update(self, obj, classname: str):
        info = self.CONTENT_INFO[classname]
        f_columns = info[0]
        f_fields = [getattr(obj, c) for c in f_columns]
        columns = info[1]
        fields = [getattr(obj, c) for c in columns]
        return self._update(info[2], columns, fields, f_columns, f_fields)

    def contains(self, obj, classname: str):
        return self.get(obj, classname) is not None

    def get(self, obj, classname: str):
        info = self.CONTENT_INFO[classname]
        columns = info[0]
        fields = [getattr(obj, c) for c in columns]
        res = self._select(info[2], columns, fields)
        if len(res) == 1:
            return res[0]
        return None

    def filter(self, obj, classname: str):
        info = self.CONTENT_INFO[classname]
        fields_map = {c: getattr(obj, c) for c in info[0] if getattr(obj, c) is not None}
        return self._select(info[2], fields_map.keys(), fields_map.values())

    def get_all(self, classname):
        return self._select(self.CONTENT_INFO[classname][2], None, None)

    def remove(self, obj, classname: str):
        info = self.CONTENT_INFO[classname]
        columns = info[0]
        fields = [getattr(obj, c) for c in columns]
        return self._delete(info[2], columns, fields)

    # Честно стырено из другого моего проекта
    # выполнение SQL запроса
    # возвращает результат запроса
    def _execute(self, query: str) -> Optional[sqlite3.Cursor]:
        try:
            res = self._base.execute(query)
            self._base.commit()
            return res
        except sqlite3.Error as e:
            logging.error('Error: {} ({}) caused by query `{}`'.format(e, type(e), query))
            return None

    # выполнение SQL запроса
    # возвращает True если были изменены записи (ровно одна если strict_one истинно)
    def _execute_query(self, query: str, strict_one: bool = False) -> bool:
        res = self._execute(query)
        if res is None:
            return False
        if strict_one:
            return res.rowcount == 1
        return res.rowcount > 0

    # возвращает id последнего добавленного ряда (для таблиц с AUTOINCREMENT)
    # возможно, стоит просто смотреть на параметр lastrowid у запроса INSERT
    def _get_last_selected_id(self) -> int:
        res = self._execute("SELECT last_insert_rowid()")
        if res is not None:
            return res.lastrowid
        return -1

    def _select(self, table: Optional[str],
                filter_columns: Optional[STR_OR_ITER],
                filter_values: Optional[STR_OR_INT_OR_ITER],
                rest: str = "",
                select_columns: Optional[Iterable[str]] = None
                ) -> List[List]:
        """
        выполнение запроса SELECT к БД - получение записей из таблицы
        параметры:
    table:              str                                                 название таблицы
    filter_columns:     str, int либо None                                  колонки, по которым будет фильтроваться
    filter_values:      str, int, либо итератор по (str|int) либо None      значения соответствующих колонок для фильра
    rest:               str                                                 дополнительный текст в конце запроса
    select_columns:     итератор либо None                                  колонки, которые возвращать
                                                                                (по умолчанию все)
        возвращает таблицу либо ее фрагмент (возможно, пустой)
        """

        # если select_columns не указан, то брать всё
        if select_columns is None:
            select_columns = '*'
        else:
            select_columns = "(" + ", ".join(select_columns) + ")"
        # первая часть запроса
        query = "SELECT " + select_columns
        if table is not None:
            query += " FROM " + table

        # если есть фильтрация, то добавить ее в запрос
        if filter_columns is not None:
            query += " WHERE " + self._construct_condition(filter_columns, filter_values)
        query += rest
        res = self._execute(query)
        if res is not None:
            return res.fetchall()
        return []

    def _insert(self,
                table: str,
                columns: Iterable[str],
                values: Iterable[STR_OR_INT]) -> bool:
        """
        выполнение запроса INSERT к БД - добавление записи
        параметры:
    table:      str                     название таблицы
    columns:    итератор по str         колонки, в которые проходить вставка (должны быть указаны все колонки в таблице)
    values:     итератор по (str|int)   значение для каждой колонки
        возвращает успешность вставки
        """
        return self._execute_query("INSERT INTO {} ({}) VALUES ({})".format(table,
                                                                            ", ".join(columns),
                                                                            ", ".join(map(self._to_str, values))))

    def _update(self,
                table: str,
                columns: STR_OR_ITER,
                values: STR_OR_INT_OR_ITER,
                filter_columns: Optional[STR_OR_ITER],
                filter_values: Optional[STR_OR_INT_OR_ITER]) -> bool:
        """
        выполнение запроса UPDATE к БД - обновление отдельных полей записей
        параметры:
    table:              str                                     название таблицы
    columns:            str либо итератор по str                изменяемые колотки
    values:             str, int либо итератор по (str|int)     значение для каждой колонки
    filter_columns:     str, int                                колонки, по которым будет фильтроваться
    filter_values:      str, int, либо итератор по (str|int)    значения соответствующих колонок для фильра
        возвращает успешность обновления
        """
        query = "UPDATE {} SET {}".format(table, self._construct_condition(columns, values, ", "))
        if filter_columns is not None:
            query += " WHERE " + self._construct_condition(filter_columns, filter_values)
        return self._execute_query(query, False)

    def _delete(self,
                table: str,
                filter_columns: Optional[STR_OR_ITER],
                filter_values: Optional[STR_OR_INT_OR_ITER]) -> int:
        """
        выполнение запроса DELETE к БД - удаление записей
        параметры:
    filter_columns:     str, int                                колонки, по которым будет фильтроваться
    filter_values:      str, int, либо итератор по (str|int)    значения соответствующих колонок для фильра
        возвращает количество удаленных записей
        """
        query = "DELETE FROM " + table
        if filter_columns is not None:
            query += " WHERE " + self._construct_condition(filter_columns, filter_values)
        res = self._execute(query)
        if res is not None:
            return res.rowcount
        return -1

    def _construct_condition(self,
                             filter_columns: STR_OR_ITER,
                             filter_values: STR_OR_INT_OR_ITER,
                             sep: str = " AND ") -> str:
        """
        построение условий для директивы WHERE (и не только)
        параметры:
    filter_columns:     str, int                                колонки, по которым будет фильтроваться
    filter_values:      str, int, либо итератор по (str|int)    значения соответствующих колонок для фильра
    sep                 str                                     разделитель. Для WHERE это " AND "
        возвращает строку с условием
        """
        # если только одна запись то всё просто
        if isinstance(filter_columns, str):
            return "{}={}".format(filter_columns, self._to_str(filter_values))
        # если это не список, то каст к нему
        if not isinstance(filter_columns, list) or not isinstance(filter_values, list):
            filter_columns, filter_values = map(list, [filter_columns, filter_values])  # convert iterable to list
        # и немного магии однострочников
        return sep.join(filter_columns[i] + "=" + self._to_str(filter_values[i]) for i in range(len(filter_columns)))

    @staticmethod
    def _to_str(val: STR_OR_INT) -> str:
        """
        преобразование аргумента в строку для SQL запроса
            (экранирование и оборачивание в кавычки строку и преобразование в строку для остальных)
    val:    str, int    аргумент
        Не-строки дополнительно кастуются к числу, потому что sqlite не умеет в bool знвчения
        """
        # int(val) converts bool to 0/1
        if isinstance(val, (int, bool)):
            return str(int(val))
        elif val is None:
            return "null"
        elif isinstance(val, str):
            return "'" + val.replace("'", "''") + "'"
        else:
            return str(val).replace("'", "''")


def import_data():
    db = Database()
    with open('create_db.sql') as file:
        queries = file.read().split(';\n\n')
        for query in queries:
            db._execute(query)
    if os.path.isfile("data/stats.json"):
        # convert dict's keys from str to int
        stats_t = json.loads(open("data/stats.json").read())
        stats = {int(dice): {int(res): stats_t[dice][res] for res in stats_t[dice]} for dice in stats_t}
        for dice, stat in stats.items():
            for roll, count in stat.items():
                db.set_stat(Stat(dice, roll, count))
    if os.path.isfile("data/custom_rolls.json"):
        custom_rolls_t = json.loads(open("data/custom_rolls.json").read())
        custom_rolls = {int(user_id): custom_rolls_t[user_id] for user_id in custom_rolls_t}
        get_field = lambda dict, key: dict[key] if key in dict else None
        for user_id, rolls in custom_rolls.items():
            for roll, roll_data in rolls.items():
                if roll == '':
                    continue
                db.set_custom_roll(CustomRoll(user_id, roll, roll_data["cnt"], roll_data["rolls_dice"],
                                              get_field(roll_data, "mod_act"), get_field(roll_data, "mod_num")))
    db.close()


if __name__ == '__main__':
    import_data()
