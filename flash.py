import subprocess
import shlex
import hashlib
import os
import sqlite3
import random
import sys
import base64

from gtts import gTTS


def printmenu(menudict):
    for item in sorted(menudict.keys()):
        print(item + ' ' + menudict.get(item))


def playflash(file):
    cmd = 'mpg123 -q ' + file
    cmd = shlex.split(cmd, posix=False)
    with subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL):
        pass


def createflash(lang, course):
    front = input('Write on the front: ')
    back = input('Write on the back: ')
    filename = hashlib.sha256(bytes(back, encoding='utf8', errors='ignore')).hexdigest() + '.mp3'
    tts = gTTS(text=back, lang=lang)
    tts.save(lang + '/' + course + '/' + filename)
    conn = sqlite3.connect(lang + '/' + course + '/data.db')
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS pyfc (id INTEGER PRIMARY KEY, front TEXT, back TEXT, filename TEXT,'
                ' box INTEGER)')
    cur.execute('INSERT INTO pyfc (front, back, filename, box) VALUES (?, ?, ?, ?)', (front, back, filename, 1))
    conn.commit()
    conn.close()
    playflash(lang + '/' + course + '/' + filename)
    selection = input('Press ENTER for next card or any key for the menu: ')
    if selection:
        processlanguage(lang, course)
        return
    else:
        createflash(lang, course)
        return


def reviewflash(lang, course, learn):
    conn = sqlite3.connect(lang + '/' + course + '/data.db')
    cur = conn.cursor()
    cur.execute('SELECT boxes,reviews FROM settings')
    settings = cur.fetchone()
    verb = 'review'
    if learn:
        verb = 'learn'
    reviewbox = int(input('Please select the box to ' + verb + ' (1-' + str(settings[0]) + '): '))
    if reviewbox in range(1, settings[0] + 1):
        cur.execute('SELECT id FROM pyfc WHERE box = ?', str(reviewbox))
        idlist = cur.fetchall()
        amount = settings[1]
        if len(idlist) < settings[1]:
            amount = len(idlist)
        idlist = random.sample(idlist, amount)
        for pyfcid in idlist:
            for front, back, filename in cur.execute('SELECT front,back,filename FROM pyfc WHERE id = ?', pyfcid):
                question = front
                if learn:
                    question = front + ' -> ' + back
                    playflash(lang + '/' + course + '/' + filename)
                answer = input(question + ' (type ! to delete entry): ')
                if len(answer) > 0:
                    if answer[0] == '!':
                        cur.execute('DELETE FROM pyfc WHERE id = ?', pyfcid)
                        conn.commit()
                        os.remove(lang + '/' + course + '/' + filename)
                        print('Entry deleted')
                    elif answer == back:
                        print('Correct')
                        if reviewbox < settings[0] and not learn:
                            cur.execute('UPDATE pyfc SET box = ? WHERE id = ?', (reviewbox + 1, pyfcid[0]))
                            conn.commit()
                        playflash(lang + '/' + course + '/' + filename)
                    else:
                        if reviewbox is not 1 and not learn:
                            cur.execute('UPDATE pyfc SET box = ? WHERE id = ?', (reviewbox - 1, pyfcid[0]))
                            conn.commit()
                        print('Wrong: ' + back)
                        playflash(lang + '/' + course + '/' + filename)
                else:
                    if reviewbox is not 1 and not learn:
                        cur.execute('UPDATE pyfc SET box = ? WHERE id = ?', (reviewbox - 1, pyfcid[0]))
                        conn.commit()
                    print('Wrong: ' + back)
                    playflash(lang + '/' + course + '/' + filename)
        conn.close()
        processlanguage(lang, course)
        return
    else:
        print('Wrong choice')
        reviewflash(lang, course, learn)
        return


def settingsmenu(lang, course):
    conn = sqlite3.connect(lang + '/' + course + '/data.db')
    cur = conn.cursor()
    cur.execute('SELECT boxes,reviews FROM settings')
    settings = cur.fetchone()
    boxes = str(settings[0])
    reviews = str(settings[1])
    menu = {'1': boxes + ' Boxes', '2': reviews + ' Reviews', '0': 'Language menu'}
    printmenu(menu)
    selection = input('Make your selection: ')
    if selection in menu:
        if selection is '0':
            conn.close()
            processlanguage(lang, course)
            return
        elif selection is '1':
            amount = input('Please select how many boxes you want: ')
            cur.execute('UPDATE settings SET boxes = ? WHERE id = 1', amount)
            conn.commit()
        elif selection is '2':
            amount = input('Please select how many reviews you want: ')
            cur.execute('UPDATE settings SET reviews = ? WHERE id = 1', amount)
            conn.commit()
    else:
        print('Wrong choice')
    conn.close()
    settingsmenu(lang, course)
    return


def processlanguage(lang, course):
    conn = sqlite3.connect(lang + '/' + course + '/data.db')
    cur = conn.cursor()
    cur.execute('SELECT name FROM sqlite_master WHERE type=\'table\' AND name=\'settings\'')
    if len(cur.fetchall()) < 1:
        cur.execute('CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, boxes INTEGER, reviews INTEGER)')
        cur.execute('INSERT INTO settings (boxes, reviews) VALUES (?, ?)', (4, 10))
        conn.commit()
    conn.close()
    menu = {'1': 'Create', '2': 'Learn', '3': 'Review', '0': 'Course menu', 's': 'Settings'}
    printmenu(menu)
    selection = input('Make your selection: ')
    if selection in menu:
        if selection is '0':
            coursemenu(lang)
            return
        elif selection is '1':
            createflash(lang, course)
            return
        elif selection is '2':
            reviewflash(lang, course, True)
            return
        elif selection is '3':
            reviewflash(lang, course, False)
            return
        elif selection is 's':
            settingsmenu(lang, course)
            return
    else:
        print('Wrong choice')
        processlanguage(lang, course)
        return


def coursemenu(lang):
    os.makedirs(lang, exist_ok=True)
    courses = []
    for root, dirs, files in os.walk(lang + '/.'):
        for entry in dirs:
            courses.append(base64.urlsafe_b64decode(entry).decode(encoding='utf8'))
        break
    menu = {'0': 'Main menu', 'c': 'Create a new course'}
    count = 0
    courses = sorted(courses)
    for entry in courses:
        count += 1
        menu[str(count)] = entry
    printmenu(menu)
    selection = input('Make your selection: ')
    if selection in menu:
        if selection is '0':
            main()
            return
        elif selection is 'c':
            name = input('Please name your course: ')
            os.makedirs(lang + '/' + base64.urlsafe_b64encode(bytes(name, encoding='utf8')).decode(encoding='utf8'),
                        exist_ok=True)
            coursemenu(lang)
            return
        else:
            processlanguage(lang,
                            base64.urlsafe_b64encode(bytes(menu[selection], encoding='utf8')).decode(encoding='utf8'))
            return
    else:
        print('Wrong choice')
        coursemenu(lang)
        return


def main():
    printmenu(gTTS.LANGUAGES)
    selection = input('Please choose a language or press ENTER to quit: ')
    if selection:
        if selection in gTTS.LANGUAGES:
            print('You chose ' + gTTS.LANGUAGES.get(selection))
            if getattr(sys, 'frozen', False):
                os.chdir(os.path.dirname(sys.executable))
            coursemenu(selection)
            return
        else:
            print('Wrong choice')
            main()

if __name__ == '__main__':
    main()
