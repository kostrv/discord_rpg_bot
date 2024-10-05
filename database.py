from game_data import locations
import sqlite3

# Подключаемся к базе данных
conn = sqlite3.connect('game.db')
cursor = conn.cursor()

def init_db():
    # Создаем таблицу игроков, если она еще не существует
    cursor.execute('''CREATE TABLE IF NOT EXISTS players (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      player_id TEXT UNIQUE,
                      current_hp INTEGER,
                      damage INTEGER,
                      max_hp INTEGER,
                      current_location_id INTEGER,
                      passed_locations TEXT,
                      current_boss_hp INTEGER,
                      FOREIGN KEY (current_location_id) REFERENCES locations(location_id)
                      )''')
    
    # Создаем таблицу локаций, если она еще не существует
    cursor.execute('''CREATE TABLE IF NOT EXISTS locations (
                      location_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      location_name TEXT UNIQUE,
                      boss_name TEXT,
                      boss_hp INTEGER,
                      boss_dmg INTEGER,
                      hp_bonus INTEGER,
                      dmg_bonus INTEGER
                      )''')
    
    # Заполняем таблицу локаций данными, если они еще не были добавлены
    cursor.executemany('''INSERT OR IGNORE INTO locations 
                          (location_name, boss_name, boss_hp, boss_dmg, hp_bonus, dmg_bonus) 
                          VALUES (?, ?, ?, ?, ?, ?)''', locations)
    
    # Сохраняем изменения в базе данных
    conn.commit()

def save_player(player_id: str, player_data: list):
    with conn:
        # Сохраняем или обновляем данные игрока
        cursor.execute('''INSERT OR REPLACE INTO players 
                          (player_id, current_hp, max_hp, damage, current_location_id, passed_locations, current_boss_hp) 
                          VALUES (?, ?, ?, ?, ?, ?, ?)''', [player_id] + player_data)

def load_player(player_id: str) -> dict | None:
    cursor.execute('''SELECT current_hp, 
                            max_hp, 
                            damage, 
                            current_location_id, 
                            passed_locations, 
                            current_boss_hp 
                            FROM players WHERE player_id = ?''', (player_id,))
    result = cursor.fetchone()
    
    # Если данные найдены, возвращаем их в виде словаря
    if result:
        current_hp, max_hp, damage, current_location_id, passed_locations, current_boss_hp = result
        return {'current_hp': current_hp, 'max_hp': max_hp, 'damage': damage, 'current_loc_id': current_location_id, 'passed_locs': passed_locations, 'current_boss_hp': current_boss_hp}
    else:
        return None

def delete_player(player_id: str):
    with conn:
        cursor.execute('DELETE FROM players WHERE player_id = ?', (player_id,))

def load_locations(loc_id: int | str = None, loc_name: str = None) -> list:
    sql = 'SELECT * FROM locations' 
    params = ()
    
    # Если передан id локации, добавляем его в запрос
    if loc_id is not None:
        if isinstance(loc_id, str) and loc_id.isdigit():
            loc_id = int(loc_id)
        sql += ' WHERE location_id = ?'
        params = (loc_id,)
    
    # Если передано имя локации, добавляем его в запрос
    elif loc_name and isinstance(loc_name, str):
        sql += ' WHERE location_name = ?'
        params = (loc_name,)

    cursor.execute(sql, params)
    result = cursor.fetchall()

    # Преобразуем результаты в список словарей с ключами
    data = []
    keys = ['id', 'name', 'boss_name', 'boss_hp', 'boss_dmg', 'hp_bonus', 'dmg_bonus']
    for val in result:
        d = dict(zip(keys, val))
        data.append(d)

    return data

def update_location(player_id: str, loc_id: int):
    with conn:
        cursor.execute('UPDATE players SET current_location_id = ? WHERE player_id = ?', (loc_id, player_id))

def update_current_boss_hp(player_id: str, val: int):
    with conn:
        cursor.execute('UPDATE players SET current_boss_hp = ? WHERE player_id = ?', (val, player_id))

def pass_location(player_id: str, loc_id: int):
    cursor.execute('SELECT passed_locations FROM players WHERE player_id = ?', (player_id,))
    result = cursor.fetchone()

    passed_locations = result[0]

    # Если игрок не прошел локации ранее, добавляем первую локацию
    if not passed_locations:
        passed_locations = str(loc_id)
    else:
        # Если есть пройденные локации, добавляем новую
        passed_locations = passed_locations + ',' + str(loc_id)
    
    with conn:
        cursor.execute('UPDATE players SET passed_locations = ? WHERE player_id = ?', (passed_locations, player_id))

def add_bonus(player_id: str, hp_bonus: int = 0, dmg_bonus: int = 0):
    with conn:
        cursor.execute('''UPDATE players SET 
                       max_hp = max_hp + ?, 
                       damage = damage + ?, 
                       current_hp = max_hp, 
                       current_boss_hp = 0 
                       WHERE player_id = ?''',  (hp_bonus, dmg_bonus, player_id))

def restore_hp(player_id: str):
    with conn:
        cursor.execute('''UPDATE players SET 
                       current_hp = max_hp
                       WHERE player_id = ?''', (player_id,))
        
def update_hp(player_id: str, player_hp: int, boss_hp: int):
    with conn:
        cursor.execute('''UPDATE players SET 
                       current_hp = ?, 
                       current_boss_hp = ?
                       WHERE player_id = ?''',  (player_hp, boss_hp, player_id))

def check_win(passed_locs: list) -> bool:
    # Получаем количество уникальных локаций в базе данных
    cursor.execute('SELECT COUNT(DISTINCT location_id) FROM locations')
    result = cursor.fetchone()
    
    # Победа, если количество пройденных локаций равно количеству локаций в базе
    return len(passed_locs) == result[0]
