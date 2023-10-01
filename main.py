from utils.dataManage import storeValue, readValue
from utils.mercadopago import checkTransaction, genPixLink
from constants import APIkey, groupId, plano1, plano2, plano3
import multiprocessing
import telebot
from telebot import types
import os, re, json, time

#Inicializa o bot
bot = telebot.TeleBot(APIkey)
#Salva o estado em que cada usuário está
state = {}
#Salva a
chronological = []

#Verifica a Sintáxe de um email
def checkEmail(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if(re.fullmatch(regex, email)):
        return True

    else:
        return False

#Em vários momentos no código é pedido uma resposta de Sim ou Não
#essa função geram Botões de Sim ou Não (Booleanos) para o usuário
#reagir
def bool_cb(cb_positive, cb_negative):
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        types.InlineKeyboardButton("Sim", callback_data=cb_positive),
        types.InlineKeyboardButton("Não", callback_data=cb_negative),
    )
    return markup

#Reação ao comando Start
@bot.message_handler(commands=['start'])
def start(msg):
    global state, chronological
    bot.send_message(msg.chat.id, f'Olá, {msg.from_user.first_name}, seja bem-vindo(a). Antes de te enviar o acesso, vamos apenas confirmar alguns dados, tudo bem?{os.linesep}Vamos lá!{os.linesep}Seu nome é {msg.from_user.first_name}?',
                     reply_markup=bool_cb('name-is-right', 'name-is-wrong'))
    #Limpa os usuários inativos do bot
    #para evitar gargalos de memória
    if msg.from_user.id in chronological:
        chronological.remove(msg.from_user.id)
    chronological.append(msg.from_user.id)
    state.update({msg.from_user.id: 'waiting for name'})
    if len(chronological) >= 1024:
        toRemove = chronological.pop(0)
        if toRemove in state:
            del state[toRemove]

@bot.message_handler(func=lambda _: True)
def handleStates(msg):
    global state
    if msg.from_user.id not in state:
        bot.send_message(msg.from_user.id, "Você está ausente a muito tempo, reinicie o bot com /start")
        return
    personal_state = state[msg.from_user.id]    
    #Após o start é pedido o nome, este trecho trata o pedido de nome e sua confirmação
    if personal_state == 'waiting for name':
        storeValue(msg.text, 'nome', msg.from_user.id)
        bot.send_message(msg.chat.id, f'{msg.text} é seu nome?', reply_markup=bool_cb(
            'name-confirm', 'name-deny'))
        state[msg.from_user.id] = None
    #Após o nome é pedido o email, este trecho trata o pedido do email
    elif personal_state == 'waiting for email':
        storeValue(msg.chat.id, 'chat-id', msg.from_user.id)
        storeValue(msg.from_user.id, 'uid', msg.from_user.id)
        #Regex que checka se o email é válido
        if (checkEmail(msg.text)):
            storeValue(msg.text, 'email', msg.from_user.id)
            bot.send_message(msg.chat.id, f'{msg.text} é seu email?', reply_markup=bool_cb(
                'email-confirm', 'email-deny'))
            state[msg.from_user.id] = None
        else:
            #caso Email seja inválido, pede novamente
            bot.send_message(
                msg.chat.id, f'{msg.text} não é um email, insira outro: ')
    #Após o email é pedido o número
    elif personal_state == 'waiting for number':
        storeValue(msg.text, 'numero', msg.from_user.id)
        bot.send_message(msg.chat.id, f'{msg.text} é seu número de celular?', reply_markup=bool_cb(
            'number-confirm', 'number-deny'))
        state[msg.from_user.id] = None


#Gerenciador de CB (callbacks)
#Em diversos momento são exibidos Botões ao usuário
#Reagir a esses Botões geram CallBacks para o código tratar
@bot.callback_query_handler(func=lambda cb: True)
def callback_manager(cb):
    global state, plano1, plano2, plano3
    #Existem 2 momentos no código em que o nome é pedido
    #já que primariamente o Bot tenta pegar o Nome cadastrado
    #no Telegram e pede pra o usuário confirmar se estiver certo
    #por isso o codigo pode aparentar estar duplicado
    #Callback que salva o Nome
    if cb.data == 'name-is-right':
        bot.send_message(cb.message.chat.id,
                         'Entendido. Seu nome será salvo...')
        storeValue(cb.from_user.first_name, 'nome', cb.from_user.id)
        state[cb.from_user.id] = 'waiting for email'
        bot.send_message(cb.message.chat.id, 'Qual o seu e-mail?')
    #Callback que pede outro nome
    elif cb.data == 'name-is-wrong':
        bot.send_message(cb.message.chat.id, 'Digite seu nome ...')
        state[cb.from_user.id] = 'waiting for name'

    #Callback que também salva o nome
    elif cb.data == 'name-confirm':
        bot.send_message(cb.message.chat.id,
                         'Entendido. Seu nome será salvo...')
        state[cb.from_user.id] = 'waiting for email'
        bot.send_message(cb.message.chat.id, 'Qual o seu e-mail?')
    #callback que também recusa o nome
    elif cb.data == 'name-deny':
        bot.send_message(cb.message.chat.id, 'Digite seu nome ...')
        state[cb.from_user.id] = 'waiting for name'

    #confimação de email
    elif cb.data == 'email-confirm':
        bot.send_message(cb.message.chat.id,
                         'Entendido. Seu email será salvo...')
        state[cb.from_user.id] = 'waiting for number'
        bot.send_message(cb.message.chat.id, 'Qual o seu número de celular?')

    #Usuário errou ao digitar o email e deseja corrigilo
    elif cb.data == 'email-deny':
        bot.send_message(cb.message.chat.id, 'Digite seu email ...')
        state[cb.from_user.id] = 'waiting for email'

    #Confirmação de número
    elif cb.data == 'number-confirm':
        bot.send_message(cb.message.chat.id, f'Escolha uma oferta para participar do grupo:{os.linesep}{plano1["name"]}-{plano1["length"]} dias - R${plano1["price"]}{os.linesep}{plano2["name"]}-{plano2["length"]} dias - R${plano2["price"]}{os.linesep}{plano3["name"]}-{plano3["length"]} dias - R${plano3["price"]}',
                         reply_markup=choosePlan()
                         )
        state[cb.from_user.id] = 'waiting for plan'
    #usuário errou ao digitar o número e deseja corrigilo
    elif cb.data == 'number-deny':
        bot.send_message(cb.message.chat.id, 'Digite seu número ...')
        state[cb.from_user.id] = 'waiting for number'

    #Callback acionado ao usuário escolher um dos planos
    #Gera um link Pix para o usuário poder pagar e adquirir sua entrada
    elif 'plan' in cb.data:
        value = cb.data.split('-')[0]
        bot.send_message(
            cb.message.chat.id, f'Gerando pix copia e cola com valor de {value}{os.linesep}Aqui está seu link:')
        bot.send_message(cb.message.chat.id,
                         f'{genPixLink(float(value), str(cb.from_user.id))}',
                         reply_markup=checkMyPayment()
                         )
        state[cb.from_user.id] = 'waiting for payment'
    
    #Ao gerar o link, gera também um botão com a escrita "Cheque meu pagamento"
    #Que ao ser clickado checka o pagamento do usuário, e se estiver pago
    #envia um link para o usuário e tira as transações no seu nome
    #Caso não esteja pago, Avisa o usuário que não houve pagamento
    elif 'checkMyPayment' in cb.data:
        user = str(cb.from_user.id)
        with open("data.json", "r") as file:
            data = json.load(file)
            if data[user]['txid'] != None:    
                try:
                    status = checkTransaction(data[user]['txid'])
                except:
                    bot.send_message(data[user]['chat-id'], "Gere outro link para pagamento")
                    bot.send_message(cb.message.chat.id, f'Escolha uma oferta para participar do grupo:{os.linesep}{plano1["name"]}-{plano1["length"]} dias - R${plano1["price"]}{os.linesep}{plano2["name"]}-{plano2["length"]} dias - R${plano2["price"]}{os.linesep}{plano3["name"]}-{plano3["length"]} dias - R${plano3["price"]}',
                         reply_markup=choosePlan()
                         )
                    state[cb.from_user.id] = 'waiting for plan'
                
                if data[user]['expires'] != None:
                    expira = int(data[user]['expires'])
                else:
                    expira = data[user]['expires']
                if status[0] == 'pending':
                    bot.send_message(data[user]['chat-id'], "Pagamento não encontrado")
                elif status[0] == 'approved':
                    if expira == None:
                        bot.unban_chat_member(groupId, user, only_if_banned=True)
                        link = bot.create_chat_invite_link(groupId, member_limit=1)
                        if float(status[1]) >= 50:
                            storeValue(daysToSeconds(999) + int(time.time()), 'expires', user)
                            bot.send_message(data[user]['chat-id'], link.invite_link)
                            storeValue(None, 'txid', user)
                        elif float(status[1]) >= 25:
                            storeValue(daysToSeconds(60) + int(time.time()), 'expires', user)
                            bot.send_message(data[user]['chat-id'], link.invite_link)
                        elif float(status[1]) > 0:
                            storeValue(daysToSeconds(30) + int(time.time()), 'expires', user)
                            bot.send_message(data[user]['chat-id'], link.invite_link)
                            storeValue(None, 'txid', user)    
                    elif time.time() >= expira:
                        if float(status[1]) >= 50:
                            storeValue(daysToSeconds(999) + int(time.time()), 'expires', user)
                            bot.send_message(data[user]['chat-id'], "Pagamento confirmado, assinatura Renovada")
                            storeValue(None, 'txid', user)
                        elif float(status[1]) >= 25:
                            storeValue(daysToSeconds(60) + int(time.time()), 'expires', user)
                            bot.send_message(data[user]['chat-id'], "Pagamento confirmado, assinatura Renovada")
                            storeValue(None, 'txid', user)
                        elif float(status[1]) > 0:
                            storeValue(daysToSeconds(30) + int(time.time()), 'expires', user)
                            bot.send_message(data[user]['chat-id'], "Pagamento confirmado, assinatura Renovada")
                            storeValue(None, 'txid', user)
                    elif time.time() < expira:
                        if float(status[1]) >= 50:
                            storeValue(daysToSeconds(plano3['length']) + expira, 'expires', user)
                            bot.send_message(data[user]['chat-id'], "Pagamento confirmado, assinatura Renovada")
                            storeValue(None, 'txid', user)
                        elif float(status[1]) >= 25:
                            storeValue(daysToSeconds(plano2['length']) + expira, 'expires', user)
                            bot.send_message(data[user]['chat-id'], "Pagamento confirmado, assinatura Renovada")
                            storeValue(None, 'txid', user)
                        elif float(status[1]) >= 15:
                            storeValue(daysToSeconds(plano1['length']) + expira, 'expires', user)
                            bot.send_message(data[user]['chat-id'], "Pagamento confirmado, assinatura Renovada")
                            storeValue(None, 'txid', user)
                            

#Mostra todos os planos ao usuário
def choosePlan():
    global plano1, plano2, plano3
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 3
    markup.add(
        types.InlineKeyboardButton(plano1['name'], callback_data=f"{plano1['price']}-plan"),
        types.InlineKeyboardButton(plano2['name'], callback_data=f"{plano2['price']}-plan"),
        types.InlineKeyboardButton(plano3['name'], callback_data=f"{plano3['price']}-plan"),
    )
    return markup

#Gera o botão "Checkar Pagamento"
def checkMyPayment():
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        types.InlineKeyboardButton("Checke meu Pagamento", callback_data="checkMyPayment"),
    )
    return markup

#Converte dias para segundos
def daysToSeconds(days):
    return days * 24 * 60 * 60

def kickPeople():
    try:
        with open('data.json', 'r') as file:
            data = json.load(file)
            for user in data:
                status = checkTransaction(data[user]['txid'])
                try:     
                    if data[user]['expires'] != None:
                        if (time.time() > int(data[user]['expires'])):
                            print('Banindo', data[user])
                            bot.ban_chat_member(groupId, user)
                            storeValue(None, 'expires', user)
                except Exception as e:
                    print(e)
        time.sleep(32*60)
    except Exception as er:
        time.sleep(16)
        kickPeople()


if __name__ == '__main__':
    kicker = multiprocessing.Process(target=kickPeople)
    kicker.start()
    while True:
        try:
            bot.polling()
        except Exception as e:
            raise e
