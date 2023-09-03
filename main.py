import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters import Text
from aiogram.utils import executor
import config
import sqlite3
from datetime import datetime
import random

# Инициализируем бота и диспетчер
storage = MemoryStorage()
bot = Bot(token=config.tgtoken)
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO)
now = datetime.now()

backtomenu = KeyboardButton('Вернуться в меню')
backtomenu_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(backtomenu)
bank = KeyboardButton('💵 Банк')
bank_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(bank)

class Form(StatesGroup):
    cardname = State()

class logsemployee(StatesGroup):
    nickname = State()
class TransferForm(StatesGroup):
    cardnum = State()
    amount = State()
    comment = State()

class clientReg(StatesGroup):
    cID = State()
    Nickname = State()

class senderForm(StatesGroup):
    sender = State()

class topup(StatesGroup):
    cardnum = State()
    tuAmount = State()

class withdrawal(StatesGroup):
    cardnum = State()
    tuAmount = State()


@dp.message_handler(commands=['start', 'bank'])
async def banking(message: types.Message):
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("SELECT * FROM cards WHERE oID = ?", (message.from_user.id,))
    card = c.fetchone()
    if card is None:
        keyboard = InlineKeyboardMarkup(row_width=1)
        buttons = [
            InlineKeyboardButton(text="Я открыл карту", callback_data="button_update"),
        ]
        keyboard.add(*buttons)
        await message.reply(f"Добро пожаловать в Бета-Банк\nДля открытия счёта сообщите данный код сотруднику отделения банка\nКод: {message.from_user.id}", reply_markup=bank_kb)
    else:
        keyboard = InlineKeyboardMarkup(row_width=1)
        buttons = [
            InlineKeyboardButton(text="💳 Перевод по номеру карты", callback_data="button_transfer"),
            InlineKeyboardButton(text="✏️ Изменить имя карты", callback_data="button_cardnamechange"),
        ]
        keyboard.add(*buttons)
        await bot.send_message(message.chat.id, f"👋 Добрый день, {card[1]}!\n💳 Карта:\n{card[2]} **{card[3]}\nБаланс: {card[4]} АР\n👇 Выберите действие", reply_markup=keyboard)

@dp.message_handler(commands=['getid'])
async def getid(message: types.Message):
    await message.reply(message.from_user.id)


@dp.callback_query_handler(lambda c: c.data.startswith('button'))
async def process_callback_button(callback_query: types.CallbackQuery):
    # Обработка выбора кнопки
    # Здесь можно добавить логику для разных кнопок
    if callback_query.data == "button_transfer":
        conn = sqlite3.connect('db.db')
        c = conn.cursor()
        c.execute("SELECT * FROM cards WHERE oID = ?", (callback_query.from_user.id,))
        card = c.fetchone()
        c.execute("SELECT * FROM ban WHERE Nickname = ?", (card[1],))
        banlist = c.fetchone()
        if banlist is None:
            await TransferForm.cardnum.set()
            await bot.send_message(callback_query.from_user.id, "💸 Отправка перевода\nВведите номер карты получателя",
                                   reply_markup=backtomenu_kb)
        else:
            await bot.send_message(callback_query.from_user.id, f'🚫 Все операции по вашему счёту приостановлены в связи с поступившим в банк запросом о наложении персональных ограничений\n{banlist[1]}\nДля снятия наличных, обратитесь в отделение банка')
    elif callback_query.data == "button_cardnamechange":
        await Form.cardname.set()
        await bot.send_message(callback_query.from_user.id, "✏️ Введите новое имя карты", reply_markup=backtomenu_kb)
    elif callback_query.data == "button_update":
        conn = sqlite3.connect('db.db')
        c = conn.cursor()
        c.execute("SELECT * FROM cards WHERE oID = ?", (callback_query.from_user.id,))
        card = c.fetchone()
        print(callback_query.from_user.id)
        if card is None:
            keyboard = InlineKeyboardMarkup(row_width=1)
            buttons = [
                InlineKeyboardButton(text="Я открыл карту", callback_data="button_update"),
            ]
            keyboard.add(*buttons)
            await callback_query.message.reply(f"Счёт не найден", reply_markup=bank_kb)
        else:
            keyboard = InlineKeyboardMarkup(row_width=1)
            buttons = [
                InlineKeyboardButton(text="💳 Перевод по номеру карты", callback_data="button_transfer"),
                InlineKeyboardButton(text="✏️ Изменить имя карты", callback_data="button_cardnamechange"),
            ]
            keyboard.add(*buttons)
            await bot.send_message(callback_query.message.chat.id,
                                   f"👋 Добрый день, {card[1]}!\n💳 Карта:\n{card[2]} **{card[3]}\nБаланс: {card[4]} АР\n👇 Выберите действие",
                                   reply_markup=keyboard)
    await bot.answer_callback_query(callback_query.id)

@dp.message_handler(Text(equals='💵 банк', ignore_case=True))
async def bank_button(message: types.Message):
    await banking(message)

@dp.message_handler(Text(equals='вернуться в меню', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Вход в меню', reply_markup=bank_kb)
    await banking(message)

@dp.message_handler(state=Form.cardname)
async def process_name(message: types.Message, state: FSMContext):
    await state.finish()
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("UPDATE cards SET Name = ? WHERE oID = ?", (message.text, message.from_user.id))
    conn.commit()
    conn.close()
    await banking(message)

@dp.callback_query_handler(lambda c: c.data.startswith('service'))
async def process_callback_button(callback_query: types.CallbackQuery):
    if callback_query.data == "service_reg":
        await clientReg.cID.set()
        await bot.send_message(callback_query.from_user.id, "Введите код предоставленный игроком", reply_markup=backtomenu_kb)
    elif callback_query.data == "service_topup":
        await topup.cardnum.set()
        await bot.send_message(callback_query.from_user.id, "Введите номер карты", reply_markup=backtomenu_kb)
    elif callback_query.data == "service_withdrawal":
        await withdrawal.cardnum.set()
        await bot.send_message(callback_query.from_user.id, "Введите номер карты", reply_markup=backtomenu_kb)

@dp.message_handler(commands=['service'])
async def service(message: types.Message):
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("SELECT * FROM Employees WHERE ID = ?", (message.from_user.id,))
    employee = c.fetchone()
    if employee is None:
        pass
    else:
        keyboard = InlineKeyboardMarkup(row_width=1)
        buttons = [
            InlineKeyboardButton(text="💳 Регистрация клиента", callback_data="service_reg"),
            InlineKeyboardButton(text="💰 Внесение наличных", callback_data="service_topup"),
            InlineKeyboardButton(text="💸 Выдача наличных", callback_data="service_withdrawal"),
        ]
        keyboard.add(*buttons)
        await bot.send_message(message.from_user.id, "✏️ Выберите действие", reply_markup=keyboard)

@dp.message_handler(commands=['sender'])
async def sender(message: types.Message):
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("SELECT * FROM Employees WHERE ID = ?", (message.from_user.id,))
    employee = c.fetchone()
    if employee is None:
        pass
    else:
        await senderForm.sender.set()
        await bot.send_message(message.from_user.id, "✏️ Напишите сообщение для рассылки", reply_markup=backtomenu_kb)


@dp.message_handler(lambda message: not message.text.isdigit(), state=TransferForm.cardnum)
async def cardnum_invalid(message: types.Message):
    return await message.reply("Номер карты состоит из 6 цифр\nВведите его повторно")

@dp.message_handler(state=TransferForm.cardnum)
async def cardnum(message: types.Message, state: FSMContext):
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("SELECT * FROM cards WHERE Number = ?", (message.text,))
    card = c.fetchone()
    if card is None:
        await message.reply("Номер карты не действителен, введите номер карты еще раз")
    else:
        async with state.proxy() as data:
            data['cardnum'] = message.text
        conn = sqlite3.connect('db.db')
        c = conn.cursor()
        c.execute("SELECT * FROM cards WHERE oID = ?", (message.from_user.id,))
        cardfrom = c.fetchone()
        c.execute("SELECT * FROM cards WHERE Number = ?", (data['cardnum'],))
        cardto = c.fetchone()
        c.execute("SELECT * FROM ban WHERE Nickname = ?", (cardto[1],))
        banlist = c.fetchone()
        if cardfrom[0] == cardto[0]:
            await bot.send_message(message.chat.id, f'🚫 Невозможно отправить перевод самому себе!', reply_markup=bank_kb)
            await state.finish()
            await banking(message)
        elif banlist is not None:
            await bot.send_message(message.chat.id, f'🚫 Невозможно выполнить перевод на данную карту, свяжитесь с получателем для уточнения реквизитов', reply_markup=bank_kb)
            state.finish()
        else:
            await TransferForm.next()
            await message.reply("💸 Введите сумму перевода")

@dp.message_handler(lambda message: not message.text.isdigit(), state=TransferForm.amount)
async def amount_invalid(message: types.Message):
    return await message.reply("🚫 Сумма состоит только из цифр!\nВведите её повторно")

@dp.message_handler(lambda message: message.text.isdigit(), state=TransferForm.amount)
async def amount(message: types.Message, state: FSMContext):
    # Update state and data
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("SELECT * FROM cards WHERE oID = ?", (message.from_user.id,))
    cardfrom = c.fetchone()
    if int(cardfrom[4]) < int(message.text):
        await message.reply("🚫 У вас недостаточно средств для перевода!")
    elif int(message.text) == 0:
        await message.reply("🚫 Нельзя перевести ноль или меньше!")
    else:
        await TransferForm.next()
        await state.update_data(amount=int(message.text))
        await message.reply("💬 Введите комментарий к переводу")

@dp.message_handler(state=TransferForm.comment)
async def comment(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['comment'] = message.text
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("SELECT * FROM cards WHERE oID = ?", (message.from_user.id,))
    cardfrom = c.fetchone()
    c.execute("SELECT * FROM cards WHERE Number = ?", (data['cardnum'],))
    cardto = c.fetchone()
    Amountcardfrom = int(cardfrom[4]) - int(data['amount'])
    c.execute("UPDATE cards SET Amount = ? WHERE oID = ?", (Amountcardfrom, message.from_user.id))
    conn.commit()
    conn.close()
    Amountcardto = int(cardto[4]) + int(data['amount'])
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("UPDATE cards SET Amount = ? WHERE Number = ?", (Amountcardto, data['cardnum']))
    conn.commit()
    conn.close()
    TransactionDateTime = now.strftime("%d.%m.%y %H:%M:%S")
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("INSERT INTO Transactions VALUES (?, ?, ?, ?)",
              (message.from_user.id, data['cardnum'], TransactionDateTime, data['amount']))
    conn.commit()
    conn.close()
    amount = data['amount']
    comment = data['comment']
    await bot.send_message(message.chat.id,
                           f'💸 Перевод отправлен\nКарта получателя: {cardto[2]} **{cardto[3]}\nСумма перевода: {amount} АР', reply_markup=bank_kb)
    await bot.send_message(cardto[0], f'⚡️ Получен перевод от {cardfrom[1]}\nКарта {cardto[2]} **{cardto[3]}\nКомментарий: {comment}\nСумма перевода: {amount} АР\nБаланс: {Amountcardto} АР')

    # Finish conversation
    await state.finish()

@dp.message_handler(state=senderForm.sender)
async def sender(message: types.Message, state: FSMContext):
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute('SELECT * FROM cards')
    rows = c.fetchall()
    c.close()
    conn.close()
    for row in rows:
        await bot.send_message(row[0], message.text)
    await message.reply(f'Рассылка завершена!\nОтправлено {len(rows)} пользователям', reply_markup=bank_kb)
    await state.finish()

@dp.message_handler(state=clientReg.cID)
async def clReg(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['cID'] = message.text
    await clientReg.next()
    await message.reply(f'Введите никнейм игрока')

@dp.message_handler(state=clientReg.Nickname)
async def clRegN(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['Nickname'] = message.text
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("SELECT * FROM ban WHERE Nickname = ?", (data['Nickname'],))
    ban = c.fetchone()
    if ban is None:
        await bot.send_message(data['cID'],
                               f'⚡️ Поздравляем с открытием счёта в Бета-Банке!\nДля начала использования нажмите на кнопку 💵 Банк')
        conn = sqlite3.connect('db.db')
        c = conn.cursor()
        cardnumber = random.randint(100000, 999999)
        c.execute("INSERT INTO cards VALUES (?, ?, ?, ?, 0)", (data['cID'], data['Nickname'], 'Бета-Карта', cardnumber))
        conn.commit()
        conn.close()
        await message.reply('✅ Счёт открыт успешно.', reply_markup=bank_kb)
        await state.finish()
    else:
        await bot.send_message(data['cID'],
                               f'🚫 Вы не можете открыть счёт в банке, поскольку на вас были наложены персональные ограничения\nИнформация о запросе на наложении ограничения изложена ниже.\n{ban[1]}')
        await message.reply(f'🚫 Отказ в открытии счёта для данного игрока\nРеференс: {ban[1]}', reply_markup=bank_kb)
        await state.finish()

@dp.message_handler(state=topup.cardnum)
async def clientTopUp(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['cardnum'] = message.text
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("SELECT * FROM cards WHERE Number = ?", (data['cardnum'],))
    card = c.fetchone()
    if card is None:
        await message.reply(f'Неверный номер карты')
    else:
        c.execute("SELECT * FROM ban WHERE Nickname = ?", (card[1],))
        ban = c.fetchone()
        if ban is None:
            await topup.next()
            await message.reply(f'Введите сумму')
        else:
            await message.reply(
                f'🚫 Отказ во внесении средств на счёт.\nСообщить клиенту о том, что все операции по счёту приостановлены и возможна только выдача наличных\nПричина: {ban[1]}',
                reply_markup=bank_kb)
            await state.finish()
@dp.message_handler(state=topup.tuAmount)
async def clientTopUpA(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['tuAmount'] = message.text
        conn = sqlite3.connect('db.db')
        c = conn.cursor()
        c.execute("SELECT * FROM cards WHERE Number = ?", (data['cardnum'],))
        card = c.fetchone()
        Amount = card[4] + int(data['tuAmount'])
        c.execute("UPDATE cards SET Amount = ? WHERE Number = ?", (Amount, data['cardnum']))
        TransactionDateTime = now.strftime("%d.%m.%y %H:%M:%S")
        c.execute("SELECT * FROM Employees WHERE ID = ?", (message.from_user.id,))
        employee = c.fetchone()
        c.execute("INSERT INTO Transactions VALUES (?, ?, ?, ?)",
                  (str(f'{employee[1]}[Office]'), data['cardnum'], TransactionDateTime,
                   data['tuAmount']))
        conn.commit()
        conn.close()
        tuamount = data['tuAmount']
        await bot.send_message(card[0],
                               f'⚡️ Внесение наличных на счёт\nКарта {card[2]} **{card[3]}\nСотрудник: {employee[1]}\nСумма: {tuamount} АР\nБаланс: {Amount} АР')
        await message.reply(f'✅ Операция выполнена успешно\nНомер карты: **{card[3]}\nВнесенная сумма: {tuamount} АР', reply_markup=bank_kb)
        await state.finish()

@dp.message_handler(state=withdrawal.cardnum)
async def clientwithdrawal(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['cardnum'] = message.text
    conn = sqlite3.connect('db.db')
    c = conn.cursor()
    c.execute("SELECT * FROM cards WHERE Number = ?", (data['cardnum'],))
    card = c.fetchone()
    if card is None:
        await message.reply(f'🚫 Введён несуществующий номер карты, введите действительный номер карты')
    else:
    
        await withdrawal.next()
        await message.reply(f'💬 Введите сумму для снятия со счёта')

@dp.message_handler(state=withdrawal.tuAmount)
async def clientwithdrawalA(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['tuAmount'] = message.text
        conn = sqlite3.connect('db.db')
        c = conn.cursor()
        c.execute("SELECT * FROM cards WHERE Number = ?", (data['cardnum'],))
        card = c.fetchone()
        if card[4] < int(data['tuAmount']):
            await message.reply(f'🚫 Недостаточно средств на счету', reply_markup=bank_kb)
            await state.finish()
        else:
            Amount = card[4] - int(data['tuAmount'])
            c.execute("UPDATE cards SET Amount = ? WHERE Number = ?", (Amount, data['cardnum']))
            TransactionDateTime = now.strftime("%d.%m.%y %H:%M:%S")
            c.execute("SELECT * FROM Employees WHERE ID = ?", (message.from_user.id,))
            employee = c.fetchone()
            c.execute("INSERT INTO Transactions VALUES (?, ?, ?, ?)",
                      (str(f'{employee[1]}[Office]'), data['cardnum'], TransactionDateTime, f"-{data['tuAmount']}"))
            conn.commit()
            conn.close()
            tuamount = data['tuAmount']
            await bot.send_message(card[0],
                                   f'⚡️ Снятие наличных со счёта\nКарта {card[2]} **{card[3]}\nСотрудник: {employee[1]}\nСумма: {tuamount} АР\nБаланс: {Amount} АР')
            await message.reply(f"✅ Операция выполнена успешно\nНомер карты: **{card[3]}\nСумма к выдаче: {data['tuAmount']} АР", reply_markup=bank_kb)
            await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False)