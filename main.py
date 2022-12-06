from dataclasses import dataclass
import json
import time
from constants import APIkey
import telebot
from telebot import types
from telebot.util import quick_markup
import os
from utils.dataManage import storeValue, readValue
from utils.mercadopago import checkTransaction, genPixLink
import multiprocessing
import re
bot = telebot.TeleBot(APIkey)
state = {}


def checkEmail(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if(re.fullmatch(regex, email)):
        return True

    else:
        return False


def bool_cb(cb_positive, cb_negative):
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        types.InlineKeyboardButton("Sim", callback_data=cb_positive),
        types.InlineKeyboardButton("Não", callback_data=cb_negative),
    )
    return markup


@bot.message_handler(commands=['start'])
def start(msg):
    global state
    bot.send_message(msg.chat.id, f'Olá, {msg.from_user.first_name}, seja bem-vindo(a). Antes de te enviar o acesso, vamos apenas confirmar alguns dados, tudo bem?{os.linesep}Vamos lá!{os.linesep}Seu nome é {msg.from_user.first_name}?',
                     reply_markup=bool_cb('name-is-right', 'name-is-wrong'))
    print(msg)
    state.update({msg.from_user.id: 'waiting for name'})


@bot.message_handler(func=lambda _: True)
def handleStates(msg):
    global state
    personal_state = state[msg.from_user.id]
    if personal_state == 'waiting for name':
        storeValue(msg.text, 'nome', msg.from_user.id)
        bot.send_message(msg.chat.id, f'{msg.text} é seu nome?', reply_markup=bool_cb(
            'name-confirm', 'name-deny'))  # colocar markup
        state[msg.from_user.id] = None
    elif personal_state == 'waiting for email':
        storeValue(msg.chat.id, 'chat-id', msg.from_user.id)
        storeValue(msg.from_user.id, 'uid', msg.from_user.id)
        if (checkEmail(msg.text)):
            storeValue(msg.text, 'email', msg.from_user.id)
            bot.send_message(msg.chat.id, f'{msg.text} é seu email?', reply_markup=bool_cb(
                'email-confirm', 'email-deny'))  # colocar markup
            state[msg.from_user.id] = None
        else:
            bot.send_message(
                msg.chat.id, f'{msg.text} não é um email, insira outro: ')

    elif personal_state == 'waiting for number':
        storeValue(msg.text, 'numero', msg.from_user.id)
        bot.send_message(msg.chat.id, f'{msg.text} é seu número de celular?', reply_markup=bool_cb(
            'number-confirm', 'number-deny'))  # colocar markup
        state[msg.from_user.id] = None
    elif state is None:
        bot.send_message(msg.chat.id, 'aio')


@bot.callback_query_handler(func=lambda cb: True)
def callback_manager(cb):
    global state
    if cb.data == 'name-is-right':
        bot.send_message(cb.message.chat.id,
                         'Entendido. Seu nome será salvo...')
        storeValue(cb.from_user.first_name, 'nome', cb.from_user.id)
        state[cb.from_user.id] = 'waiting for email'
        bot.send_message(cb.message.chat.id, 'Qual o seu e-mail?')
    elif cb.data == 'name-is-wrong':
        bot.send_message(cb.message.chat.id, 'Digite seu nome ...')
        state[cb.from_user.id] = 'waiting for name'

    elif cb.data == 'name-confirm':
        bot.send_message(cb.message.chat.id,
                         'Entendido. Seu nome será salvo...')
        state[cb.from_user.id] = 'waiting for email'
        bot.send_message(cb.message.chat.id, 'Qual o seu e-mail?')
    elif cb.data == 'name-deny':
        bot.send_message(cb.message.chat.id, 'Digite seu nome ...')
        state[cb.from_user.id] = 'waiting for name'

    elif cb.data == 'email-confirm':
        bot.send_message(cb.message.chat.id,
                         'Entendido. Seu email será salvo...')
        state[cb.from_user.id] = 'waiting for number'
        bot.send_message(cb.message.chat.id, 'Qual o seu número de celular?')
    elif cb.data == 'email-deny':
        bot.send_message(cb.message.chat.id, 'Digite seu email ...')
        state[cb.from_user.id] = 'waiting for email'

    elif cb.data == 'number-confirm':
        bot.send_message(cb.message.chat.id, f'Entendido. Seu número será salvo...{os.linesep}Escolha uma oferta para participar do grupo:{os.linesep}Bronze-30 dia(s) - 15,00{os.linesep}Prata- 60 dia(s)- 25,00{os.linesep}Ouro- 999 dia(s)-50,00',
                         reply_markup=choosePlan()
                         )
        state[cb.from_user.id] = 'waiting for plan'
    elif cb.data == 'number-deny':
        bot.send_message(cb.message.chat.id, 'Digite seu número ...')
        state[cb.from_user.id] = 'waiting for number'
    elif 'plan' in cb.data:
        value = cb.data.split('-')[0]
        bot.send_message(
            cb.message.chat.id, f'Gerando pix copia e cola com valor de {value}{os.linesep}Aqui está seu link:')
        bot.send_message(cb.message.chat.id,
                         f'{genPixLink(float(value), str(cb.from_user.id))}')
        state[cb.from_user.id] = 'waiting for payment'


def choosePlan():
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 3
    markup.add(
        types.InlineKeyboardButton("Bronze", callback_data="15-plan"),
        types.InlineKeyboardButton("Prata", callback_data="25-plan"),
        types.InlineKeyboardButton("Ouro", callback_data="50-plan"),
        types.InlineKeyboardButton("Teste", callback_data="0.01-plan")
    )
    return markup


def daysToSeconds(days):
    return days * 24 * 60 * 60


def checkPayments():
    while True:
        time.sleep(5)
        with open('data.json', 'r') as file:
            data = json.load(file)
            for user in data:
                status = checkTransaction(data[user]['txid'])
                print(status[0], '||', data[user]['nome'])
                try:     
                    if data[user]['expires'] != None:
                        if (time.time() > int(data[user]['expires'])):
                            print('Banindo', data[user])
                            bot.ban_chat_member(-670386948, user)
                            storeValue(None, 'expires', user)
                except:
                    print(data[user],'ERRO no banimento')
                if status[0] == 'approved':
                    link = bot.create_chat_invite_link(
                        -670386948, member_limit=1)
                    if float(status[1]) >= 50:
                        storeValue(daysToSeconds(999) +
                                   int(time.time()), 'expires', user)
                        bot.send_message(
                            data[user]['chat-id'], link.invite_link)
                        storeValue(None, 'txid', user)
                    elif float(status[1]) >= 25:
                        storeValue(daysToSeconds(60) +
                                   int(time.time()), 'expires', user)
                        bot.send_message(
                            data[user]['chat-id'], link.invite_link)
                        storeValue(None, 'txid', user)
                    elif float(status[1]) >= 0:
                        storeValue(daysToSeconds(30) +
                                   int(time.time()), 'expires', user)
                        print(data[user]['chat-id'])
                        bot.send_message(
                            data[user]['chat-id'], link.invite_link)
                        storeValue(None, 'txid', user)

            time.sleep(5)


if __name__ == '__main__':
    checker = multiprocessing.Process(target=checkPayments)
    checker.start()
    while True:
        try:
            bot.polling()
        except:
            time.sleep(5)
