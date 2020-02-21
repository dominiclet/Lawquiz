import requests
import json
import time
from openpyxl import load_workbook
from random import randint


TOKEN = "1078456189:AAFUHlvqFpqLUqUPezNx2_0l1_fRZuxK1Ro"
URL = "https://api.telegram.org/bot{}/".format(TOKEN)


#a 'get' request, returns json content
def get_url(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content

#parses json content
def get_json(url):
    content = get_url(url)
    parsed_js = json.loads(content)
    return parsed_js

#get updates - allows you to specify offset so that not all messages are downloaded
def get_updates(offset=None):
    url = URL + "getUpdates?timeout=100"
    if offset:
        url += "&offset={}".format(offset)
    js = get_json(url)
    return js

#get info of the last update received
def last_text_chat(offset):
    all_info = get_updates(offset)
    no_messages = len(all_info['result'])
    #handles the situation where no messages sent and long polling timeout
    if no_messages == 0:
        return 1

    # only return info if get request returns a chat update
    if 'text' in all_info['result'][no_messages - 1]['message']:
        # get update ID for offset
        update_id = all_info['result'][no_messages - 1]['update_id']
        #get last text, chat id, name, time
        chat = all_info['result'][no_messages - 1]['message']['chat']['id']
        name = all_info['result'][no_messages - 1]['message']['from']['first_name'] + all_info['result'][no_messages - 1]['message']['from']['last_name']
        text = all_info['result'][no_messages - 1]['message']['text']
        time = all_info['result'][no_messages - 1]['message']['date']
        #[0]=update_id, [1]=chat, [2]=name, [3]=text
        return update_id, chat, name, text, time

    return 0

#preps a reply_markup json object (array of buttons)
def custom_keyboard(*args):
    buttons = []
    keyboard = {'keyboard':buttons}
    for arg in args:
        buttons.append([{'text':arg}])
    keyboard = json.dumps(keyboard)
    return keyboard

#sends a message to the relevant chat
def send_message(text, chat_id, reply_markup = None):
    if reply_markup == None:
        url = URL + "sendMessage?text={}&chat_id={}".format(text, chat_id)
        get_url(url)
    else:
        url = URL + "sendMessage?text={}&chat_id={}&reply_markup={}".format(text, chat_id, reply_markup)
        get_url(url)

#outputs blanks in place of word
def blank_maker(word):
    blanks = ""
    for letter in word:
        if letter == " ":
            blanks += "  "
        else:
            blanks += "_ "
    return blanks


class Quizsettings:
    """stores setting info for quiz"""
    #[{'chat': chat, 'topic': topic, 'rounds': round counter, 'bout': bout counter (optional), 'question': stored question (optional), 'answer': stored answer (optional), avoid': question no. to avoid (optional)}, another dict, another dict, etc.]
    def __init__(self):
        self.all = []
        self.wb = load_workbook(filename = 'quiz.xlsx', read_only=True)

    def addtopic(self, chat, topic):
        self.all.append({'chat': chat, 'topic': topic})

    def addrounds(self, chat, rounds):
        for dict in self.all:
            if dict["chat"] == chat:
                if rounds == '10 rounds':
                    dict['rounds'] = 10
                elif rounds == '20 rounds':
                    dict['rounds'] = 20
                elif rounds == 'Unlimited':
                    dict['rounds'] = None

                #prep for bout counter
                dict['bout'] = 0
                #prep for questions to avoid
                dict['avoid'] = []

    def getsettings(self, chat):
        #returns dictionary of settings, if chat settings does not exist, return none
        for dict in self.all:
            if dict['chat'] == chat:
                return dict
        return None

    def delete(self, chat):
        for index, dict in enumerate(self.all):
            if dict['chat'] == chat:
                self.all.pop(index)

    def run_quiz(self, chat, name, text):
        chat_setting = self.getsettings(chat)
        if chat_setting == None:
            return "Error: No quiz found"

        if chat_setting['topic'] == "Latin terms":
            sheet = self.wb['latin']

        #first bout
        if chat_setting['bout'] == 0:
            #check if question had already appeared
            while True:
                question_no = randint(2,318)
                print(question_no)
                if question_no not in chat_setting['avoid']:
                    break

            question = sheet['A'+ str(question_no)].value
            answer = sheet['B'+ str(question_no)].value
            blanks = blank_maker(answer)
            #store question no to avoid
            chat_setting['avoid'].append(question_no)
            #store question and answer
            chat_setting['question'] = question
            chat_setting['answer'] = answer
            #send question
            send_message(question + "\n\n" + blanks, chat)
            chat_setting['bout'] += 1

        elif chat_setting['bout'] == 1:
            if text.lower() == chat_setting['answer'].lower():
                send_message("Congratulations " + name + "!\n\nThe correct answer is " + chat_setting['answer'] +".", chat)



if __name__ == "__main__":
    offset = None
    #lists to retain stages of chats - stage 1: pick a topic, stage 2: how many rounds, stage 3: Q & A
    stage_1 = []
    stage_2 = []
    stage_3 = []

    Settings = Quizsettings()
    while True:
        chat_info = last_text_chat(offset)
        if isinstance(chat_info, tuple):
            update_id, chat, name, text, time = chat_info

            if text == "/end@Lawquiz_bot":
                if chat in stage_1:
                    stage_1.remove(chat)
                    Settings.delete(chat)
                elif chat in stage_2:
                    stage_2.remove(chat)
                    Settings.delete(chat)
                elif chat in stage_3:
                    stage_3.remove(chat)
                    Settings.delete(chat)
                buttons = custom_keyboard('Start quiz')
                send_message("Okay, ended", chat, buttons)

            #stage 1
            elif chat in stage_1:
                if text == 'All' or text == 'Latin terms':
                    buttons = custom_keyboard('10 rounds', '20 rounds', 'Unlimited')
                    send_message("How many rounds?", chat, buttons)
                    stage_1.remove(chat)
                    stage_2.append(chat)
                    Settings.addtopic(chat, text)

            #stage 2
            elif chat in stage_2:
                if text == '10 rounds' or text == '20 rounds' or text == 'Unlimited':
                    Settings.addrounds(chat, text)
                    stage_2.remove(chat)
                    stage_3.append(chat)
                    #send initialisation messages
                    send_message("Starting quiz...", chat)

            #stage 3
            if chat in stage_3:
                Settings.run_quiz(chat, name, text)


            elif text == "Start quiz" or text == "/start" or text == "/start@Lawquiz_bot":
                buttons = custom_keyboard('All', 'Latin terms')
                send_message("Welcome to Lawquiz! Pick a topic.", chat, buttons)
                stage_1.append(chat)
            offset = update_id + 1
        elif chat_info == 0:
            print("Either new chat created, bot removed, or bot added")
            offset = update_id + 1
        elif chat_info == 1:
            print("Long polling timeout")
