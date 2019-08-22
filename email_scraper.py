# stdlib
import time
import os
import json
import base64
import string
import glob
import imaplib
import email

# 3rd party
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import pandas as pd
import pyautogui


def start_chromedriver():
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome("chromedriver.exe", options=options)
    driver.set_page_load_timeout(60)
    driver.maximize_window()
    driver.implicitly_wait(3)
    return driver


def filter_chars(value):
    '''filters out chars that break files'''
    string_value = (str(value).replace('\n', '').replace('/', '')
                    .replace("\"", '').replace('?', '').replace('%', '')
                    .replace('*', '').replace(':', '').replace('|', '')
                    .replace('"', '').replace('<', '').replace('>', '')
                    .replace('.', '').replace('!', ''))
    return ''.join(list(filter(lambda x: x in string.printable, string_value)))


def fp_screenshot(driver: webdriver.Chrome):
    def send(cmd, params):
        resource = (f'/session/{driver.session_id}/chromium/'
                    f'send_command_and_get_result')
        url = driver.command_executor._url + resource
        body = json.dumps({'cmd': cmd, 'params': params})
        response = driver.command_executor._request('POST', url, body)
        return response.get('value')

    def evaluate(script):
        response = send('Runtime.evaluate', {'returnByValue': True,
                        'expression': script})
        return response['result']['value']

    metrics = evaluate(
        "({"
        "width: Math.max(window.innerWidth, document.body.scrollWidth,"
        "document.documentElement.scrollWidth)|0,"
        "height: Math.max(innerHeight, document.body.scrollHeight,"
        "document.documentElement.scrollHeight)|0,"
        "deviceScaleFactor: window.devicePixelRatio || 1,"
        "mobile: typeof window.orientation !== 'undefined'"
        "})")
    send('Emulation.setDeviceMetricsOverride', metrics)
    screenshot = send('Page.captureScreenshot', {'format': 'png',
                      'fromSurface': True})
    send('Emulation.clearDeviceMetricsOverride', {})

    return base64.b64decode(screenshot['data'])


def fp_ss(driver: webdriver.Chrome, image: str = "screenshot.png"):
    png = fp_screenshot(driver)
    with open(image, 'wb') as f:
        f.write(png)


metadata = []
timestamp = (time.strftime('%m-%d-%y', time.localtime()))
wk_dir = (f'path/to/directory/EmailScraper/EmailScraper {timestamp}')
fpath_images = f'{wk_dir}/*.png'
login = str(input('enter your email: '))
pw = str(input('enter your password: '))
smtp_port = 993

# click on an email, click gmail's "print" button (not the PC's) and then copy
# the URL up to "thread-f%3A". the 1st half of the URL will be the same for all
# emails on that particular account. the pulled thread ID from imap will
# combine to form the full direct-to-that-email URL
url1 = ('https://mail.google.com/mail/example-url')

os.makedirs(wk_dir, exist_ok=True)

# connects to gmail account and creates a list of all unread emails
mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login(login, pw)
mail.select('inbox')
typ, data = mail.uid('search', None, '(UNSEEN)')
mail_list = data[0].split()

driver = start_chromedriver()

for thing in mail_list:
    meta = {}

    # gets the thread ID to build a direct URL for chromedriver
    result, data = mail.uid('fetch', thing, '(X-GM-MSGID)')
    msg = data[0].decode('utf-8')
    discard, msgid = msg.split('X-GM-MSGID')
    msgid, discard = msgid.split('UID')
    msgid = msgid.replace(' ', '')
    url = url1 + msgid

    # body of the email
    result2, data2 = mail.uid('fetch', thing, '(RFC822)')
    msg2 = data2[0][1]
    message = email.message_from_bytes(msg2)

    # keeps only the sender name, discarding the mail address
    retailer = message['From'].split()[0].replace('"', '')
    date = str(email.utils.parsedate_to_datetime(message['Date']))
    subject = message['Subject']
    promo_name = f'email {date} {retailer}'
    meta['retailer'] = retailer
    meta['subject'] = subject
    meta['date'] = date
    meta['url'] = url
    meta['promo_name'] = promo_name
    print(retailer)
    print(subject)
    print(date)

    # goes to the email's URL
    driver.get(url)
    time.sleep(4)

    # logs in if login screen loads
    try:
        driver.find_element_by_id('identifierId').send_keys(login)
        time.sleep(1)
        driver.find_element_by_id('identifierNext').click()
        time.sleep(2)
        driver.find_element_by_name('password').send_keys(pw)
        time.sleep(1)
        driver.find_element_by_id('passwordNext').click()
        time.sleep(4)
    except NoSuchElementException:
        pass

    # escape to remove the printer overlay, then fullpage screenshots the email
    pyautogui.press('esc')
    time.sleep(2)

    # checks if there are same-named files already in the dir (2+ email from
    # one retailer in a single day)
    for img in glob.glob(fpath_images):
        if promo_name in fpath_images:
            promo_name = filter_chars(f'{promo_name} {subject[:15]}')

    file_name = f'{wk_dir}/{promo_name}.png'
    fp_ss(driver=driver, image=f'{wk_dir}/{file_name}')
    metadata.append(meta)

driver.close()

# saves metadata to a CSV in the working directory
if len(metadata) > 0:
    df = pd.DataFrame(metadata, columns=['promo_name',
                                         'retailer',
                                         'date',
                                         'subject',
                                         'url'
                                         ])
    df.to_csv(f'{wk_dir}/metadata {timestamp}.csv', index=False)
