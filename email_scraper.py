# stdlib
import time
import os
import string
import json
import base64
import imaplib
import email

# 3rd party
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from pandas import DataFrame
import emoji


def start_chromedriver():
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(
        "/example/driver/filepath/",
        options=options
    )
    driver.set_page_load_timeout(60)
    driver.maximize_window()
    driver.implicitly_wait(3)
    return driver


def unshadow(element):
    '''expands a page's shadow-root
    '''
    shadow_root = driver.execute_script(
        'return arguments[0].shadowRoot',
        element
    )
    return shadow_root


def fp_screenshot(driver: webdriver.Chrome):
    '''Gets a full-page screenshot. Copied from blog.arkfeng.xyz
    '''
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
    ''' Takes full-page screenshot and saves to file path'''
    png = fp_screenshot(driver)
    with open(image, 'wb') as f:
        f.write(png)


def filter_chars(value):
    '''filters out chars that break files or break internal file naming
    convention'''
    string_value = (str(value).replace('/', '')
                    .replace("\"", '').replace('?', '').replace('%', '')
                    .replace('*', '').replace(':', '').replace('|', '')
                    .replace('"', '').replace('<', '').replace('>', '')
                    .replace('!', '').replace('\n', '')
                    )
    return ''.join(list(filter(lambda x: x in string.printable, string_value)))


def remove_emoji(text):
    return emoji.get_emoji_regexp().sub(u'', text)


metadata = []
timestamp = time.strftime('%m-%d-%y', time.localtime())
wd = f'example/filepath/email_scraper/email_scraper_{timestamp}'
login = str(input('enter your gmail login: '))
print(f'Scraping emails for {login}')
pw = str(input('enter your password: '))
smtp_port = 993
url1 = (
    'https://mail.google.com/mail/u/0?ik=99dd2cc95d&view=pt&search='
    'all&permthid=thread-f%3A'
)

os.makedirs(wd, exist_ok=True)

# connects to gmail account and creates a list of all unread emails
mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login(login, pw)
mail.select('inbox')
typ, data = mail.uid('search', None, '(UNSEEN)')
mail_list = data[0].split()
print(f'{len(mail_list)} unread emails.')
i = 1

driver = start_chromedriver()

for thing in mail_list:
    meta = {}
    print(f'Email {i} of {len(mail_list)}')

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
    retailer, discard = message['From'].split(' <')
    retailer = retailer.replace('"', '')

    # removes various fluff words from retailer name
    if 'GameStop' in retailer:
        retailer = 'GameStop'
    elif 'Best Buy' in retailer:
        retailer = 'Best Buy'
    elif 'Walmart' in retailer:
        retailer = 'Walmart'

    # transforms date to mm.dd.yy format, for client's filename requirement
    date1 = str(email.utils.parsedate_to_datetime(message['Date']))[:10]
    date2 = date1[5:].replace('-', '.')
    year = date1[2:4]
    date = date2 + '.' + year

    # opens the email in chromedriver
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

    # switches to chrome://print/ window overlay
    handles = driver.window_handles
    original_handle = driver.current_window_handle
    for handle in handles:
        if handle == original_handle:
            handles.remove(handle)
    driver.switch_to.window(handles[0])

    # opens shadow roots and clicks the cancel button to close print overlay
    root1 = driver.find_element_by_css_selector('print-preview-app')
    shadow1 = unshadow(root1)
    root2 = shadow1.find_element_by_css_selector('print-preview-sidebar')
    shadow2 = unshadow(root2)
    root3 = shadow2.find_element_by_css_selector('print-preview-button-strip')
    shadow3 = unshadow(root3)
    cancel_button = shadow3.find_element_by_css_selector('.cancel-button')
    cancel_button.click()

    # switches back to main window
    driver.switch_to.window(original_handle)

    subject = (
        driver.find_element_by_xpath('//div[@class="maincontent"]/table').text
    )

    # gets rid of unwanted fluff and emojis in subject
    subject = (
        subject.replace('\n1 message', '')
        .replace('[External Public Use]', '')
        .replace('FW: ', '')
        .replace('SamOsburn', '(Name)')
        .replace('Eedar', '(Name)')
        .replace('eedar retail', '(Name)')
        .replace('eedar', '(Name)')
        .replace('\n', '')
    )
    subject = remove_emoji(subject)

    # modifies sender / date / subject if forwarded email
    if 'Corey' in retailer:
        if 'PS4' in subject[:3]:
            retailer = 'PlayStation'
            date = subject[4:12]
            subject = subject[13:]
        elif 'GS' in subject[:3]:
            retailer = 'GameStop'
            date = subject[3:11]
            subject = subject[12:]

    # modified subject breaking off at the end of a word, for client's filename
    # requirement
    modded_subject = subject[:20]
    split = modded_subject.rfind(' ')
    modded_subject = modded_subject[:split] + '...'

    # gets rid of characters that break file names
    modded_subject = filter_chars(modded_subject)
    promo_name = f'email - {date} - {retailer} - {modded_subject}'
    print(promo_name)

    meta['promo_name'] = promo_name
    meta['retailer'] = retailer
    meta['subject'] = subject
    meta['date'] = date
    meta['url'] = url
    file_name = f'{wd}/{promo_name}.png'
    time.sleep(1)

    fp_ss(driver=driver, image=file_name)
    metadata.append(meta)
    i += 1

driver.close()

# saves metadata to a CSV in the working directory
if len(metadata) > 0:
    df = DataFrame(
        metadata,
        columns=[
            'retailer',
            'date',
            'subject',
            'url'
        ]
    )
    df.to_csv(
        f'{wd}/metadata_{timestamp}.csv',
        index=False,
        encoding='utf-8-sig'
    )
    print('metadata saved to CSV.')
