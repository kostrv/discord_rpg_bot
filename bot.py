from discord.ext import commands
from dotenv import load_dotenv
from game_data import msgs
import database as db
import discord
import os

db.init_db()

load_dotenv()
token = os.getenv(key='TOKEN')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready(): 
    print(msgs['ready'].format(bot.user))

@bot.command(name='start')
async def start_game(ctx):
    # Инициализируем значения
    player = ctx.author
    player_id = str(player.id)
    
    # Получаем данные
    player_data = db.load_player(player_id)
    
    if not player_data: # Если игрок еще не в игре, добавляем стартовые данные в бд
        base_values = [100, 100, 15, 0, '', 0]
        db.save_player(player_id=player_id, 
                       player_data=base_values)
        
        # Информируем пользователя
        await ctx.send(msgs['welcome'])
        await status(ctx) # Вызываем функцию для просмотра характеристик
        
    else: # Если игрок уже начал, отправляем сообщение
        await ctx.send(msgs['started'].format(player.mention))

@bot.command(name='status')
async def status(ctx):
    # Инициализируем значения
    player = ctx.author
    player_id = str(player.id)
    
    # Получаем данные
    player_data = db.load_player(player_id)
    locs_data = db.load_locations()

    # Проверяем нахождение в игре
    if not player_data:
        await ctx.send(msgs['start'].format(player.mention))
        return

    # Извлекаем значения игрока
    current_hp = player_data['current_hp']
    max_hp = player_data['max_hp']
    damage = player_data['damage']
    player_loc_id = player_data['current_loc_id']

    # Получаем список из id пройденных локаций 
    passed_locs_ids = player_data['passed_locs'].split(',') if player_data['passed_locs'] else []
    
    current_loc = 'Дорога в деревню'
    passed_locs = []

    for loc in locs_data:
        loc_id = str(loc['id'])

        # Определяем текущую локацию
        if loc_id == str(player_loc_id):
            current_loc = loc['name']

        # Собираем названия пройденных локаций 
        if loc_id in passed_locs_ids:
            passed_locs.append(loc['name'])

    if not passed_locs:
        passed_locs = ['Отсутствуют']

    await ctx.send(msgs['status'].format(
        player.mention,
        current_hp,
        max_hp,
        damage,
        current_loc,
        ', '.join(passed_locs)
    ))
          
@bot.command(name='map')
async def map(ctx):
    # Инициализируем значения
    player = ctx.author
    player_id = str(player.id)
    
    # Получаем данные
    player_data = db.load_player(player_id)
    locs_data = db.load_locations()

    # Проверяем нахождение в игре
    if not player_data:
        await ctx.send(msgs['start'].format(player.mention))
        return

    msg_data = [f'{player.mention}\n']
    
    # Подготавливаем часто используемые значения
    passed_locs = player_data['passed_locs'].split(',')
    current_loc_id = str(player_data['current_loc_id'])

    # Проходимся по локациим и добавляем информацию о них
    for data in locs_data:
        loc_id = str(data['id'])

        # Определяем статус игрока на локации
        if loc_id == current_loc_id:
            status = 'Текущая локация'
        elif loc_id in passed_locs:
            status = 'Пройдено'
        else:
            status = 'Не исследовано'

        # Создаем сообщение с данными по локации
        msg = msgs['locinfo'].format(
            data['id'], 
            data['name'], 
            status, 
            data['boss_name'], 
            data['boss_hp'], 
            data['boss_dmg'], 
            data['hp_bonus'], 
            data['dmg_bonus']
        )
        msg_data.append(msg)

    await ctx.send('\n'.join(msg_data))
    
@bot.command(name='go')
async def go(ctx, location: str = None):
    # Инициализируем значения
    player = ctx.author
    player_id = str(player.id)
    player_mention = player.mention
    
    # Получаем данные
    player_data = db.load_player(player_id)

    # Проверяем нахождение в игре
    if not player_data:
        await ctx.send(msgs['start'].format(player_mention))
        return

    # Проверяем указание аргумента
    if location is None:
        await ctx.send(msgs['goerror'].format(player_mention))
        return

    # Получаем информацию по локации, в зависимости от типа аргумента
    loc_data = db.load_locations(loc_id=int(location)) if location.isdigit() else db.load_locations(loc_name=location)

    # Если такой локации нет, информируем пользователя
    if not loc_data:
        await ctx.send(msgs['wrongloc'].format(player_mention, location))
        return

    # Инициализируем значения для удобства
    loc_data = loc_data[0]  # Оставляем только список
    loc_id = loc_data['id']
    loc_name = loc_data['name']

    # Проверяем, находится ли уже игрок на данной локации
    if loc_id == player_data['current_loc_id']:
        await ctx.send(msgs['alreadyonloc'].format(player_mention, loc_name))
        return

    # Проверяем, прошел ли уже игрок данную локацию
    passed_locs = player_data['passed_locs'].split(',')
    if str(loc_id) in passed_locs:
        await ctx.send(msgs['onpassedloc'].format(player_mention, loc_name))
        return

    # Обновляем текущую локацию и устанавливаем хп босса конкретно для игрока
    db.update_location(player_id=player_id, loc_id=loc_id)
    db.update_current_boss_hp(player_id=player_id, val=loc_data['boss_hp'])

    # Информируем пользователя и передаем данные о локации
    await ctx.send(msgs['bossmeet'].format(
        player_mention,
        loc_name,
        loc_data['boss_name'],
        loc_data['boss_hp'],
        loc_data['boss_dmg']
    ))
       
@bot.command(name='attack')
async def attack(ctx):
    # Инициализируем значения
    player = ctx.author
    player_id = str(player.id)

    # Получаем данные
    player_data = db.load_player(player_id)
    
    if not player_data:
        await ctx.send(msgs['start'].format(player.mention))
        return

    loc_id = player_data['current_loc_id']
    locations = db.load_locations(loc_id=loc_id)
    if not locations:
        await ctx.send(msgs['noenemy'])
        return
    loc = locations[0]

    # Инициализируем значения для удобства
    player_dmg = player_data['damage']
    player_hp = player_data['current_hp']
    boss_name = loc['boss_name']
    boss_dmg = loc['boss_dmg']
    boss_hp = player_data['current_boss_hp']
    hp_bonus = loc['hp_bonus']
    dmg_bonus = loc['dmg_bonus']

    # Проверяем, не побежден ли уже босс
    if boss_hp == 0:
        await ctx.send(msgs['alreadydead'].format(player.mention, boss_name))
        return

    # Игрок атакует босса
    await ctx.send(msgs['attack'].format(player.mention, boss_name, player_dmg))
    boss_hp -= player_dmg

    # Проверяем, был ли босс побежден
    if boss_hp <= 0:
        # Добавляем локацию в список пройденных
        db.pass_location(player_id=player_id, loc_id=loc['id'])
        await ctx.send(msgs['bossdefeat'].format(boss_name))
        
        # Добавляем бонусы к характеристикам и востанавливаем хп
        db.add_bonus(player_id=player_id, hp_bonus=hp_bonus, dmg_bonus=dmg_bonus)
        db.restore_hp(player_id=player_id)
        
        player_data = db.load_player(player_id)  # Получаем обновленные данные
        await ctx.send(msgs['bonus'].format(player.mention,
                                            player_data['max_hp'], 
                                            hp_bonus, 
                                            player_data['damage'], 
                                            dmg_bonus))
        
        # Проверяем, выиграл ли игрок игру
        if db.check_win(passed_locs=player_data['passed_locs'].split(',')):
            await ctx.send(msgs['win'].format(player.mention))
            db.delete_player(player_id)
    else:
        # Босс атакует игрока
        await ctx.send(msgs['attack'].format(boss_name, player.mention, boss_dmg))
        player_hp -= boss_dmg

        # Проверяем, был ли игрок побежден
        if player_hp <= 0:
            await ctx.send(msgs['gameover'].format(player.mention))
            db.delete_player(player_id)
            return

        # Обновляем значения хп в бд
        db.update_hp(player_id=player_id, player_hp=player_hp, boss_hp=boss_hp)
        await ctx.send(msgs['fightstatus'].format(boss_hp, player_hp))

@bot.command(name='help')
async def help_command(ctx):
    await ctx.send(msgs['help'])    

if __name__ == '__main__':
    bot.run(token=token)
