# stdlib
import glob
import os
import shutil
import string
import time

# 3rd party
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from pandas import DataFrame


def start_chromedriver():
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument('--ignore-ssl-errors')
    driver = webdriver.Chrome('path/to/driver/chromedriver.exe', options=options)
    driver.set_page_load_timeout(40)
    driver.maximize_window()
    driver.implicitly_wait(3)
    return driver


def filter_chars(value):
    '''filters out chars that break files or break internal file naming
    convention'''
    string_value = (str(value).replace('-', '').replace('/', '')
                    .replace("\"", '').replace('?', '').replace('%', '')
                    .replace('*', '').replace(':', '').replace('|', '')
                    .replace('"', '').replace('<', '').replace('>', '')
                    .replace('.', '').replace('!', ''))
    return ''.join(list(filter(lambda x: x in string.printable, string_value)))


ended_list = []
url_dict = {'main': 'https://www.walmart.com/',
            'games': 'https://www.walmart.com/cp/video-games/2636',
            'xb1': ('https://www.walmart.com/cp/xbox-one-consoles,-games-and-'
                    'accessories/1224908'),
            'ps4': ('https://www.walmart.com/cp/playstation-4-consoles-games-'
                    'controllers-more/1102672'),
            'ns': 'https://www.walmart.com/cp/nintendo-switch/4646529'
            }

# Creates directories for the day.
timestamp = time.strftime('%m-%d-%y', time.localtime())
timestamp_folder = time.strftime('%m-%d-%y--%I-%M %p', time.localtime())
wk_dir = f'example/path/walmart_scraper/walmart_{timestamp_folder}'
ref_dir = 'example/path/walmart_scraper/reference_directory'
fpath_images = wk_dir + '/*.png'
fpath_ref_images = ref_dir + '/*.png'
fpath_already_active = wk_dir + '/active'
os.makedirs(wk_dir, exist_ok=True)
os.makedirs(fpath_already_active, exist_ok=True)
driver = start_chromedriver()

# loops through each URL and captures promos
for url in url_dict:
    i = 0
    driver.get(url_dict[url])
    time.sleep(4)

    # different possible carousel element names
    box = driver.find_element_by_css_selector('.POVCarousel, .MultiLinkPOVCarousel')
    promos = box.find_elements_by_css_selector('.slider-slide')
    print(f'{url}: {len(promos)} promos')
    for promo in promos:

        # finds list of buttons each time since the element changes once it is
        # clicked
        buttons = box.find_elements_by_css_selector(
            'button.carousel-paginator-item'
        )
        if buttons:
            buttons[i].click()
            time.sleep(.5)
            i += 1

        try:
            name = promo.find_element_by_css_selector('.ClickThroughImage-link')
            name = name.get_attribute('title')
        except NoSuchElementException:
            name = f'product {i + 1}'
        name = filter_chars(name)

        # reduces the 'product' name so that the eventual full filepath
        # doesn't exceed windows char limit
        if len(name) > 100:
            diff = len(name) - 100
            name = name[:-diff]
        print(name)
        file_name = f'{wk_dir}/web {url} - {name} - promo.png'
        driver.save_screenshot(file_name)
        time.sleep(.5)

driver.close()

new_list = [os.path.basename(img) for img in glob.glob(fpath_images)]
active_list = [os.path.basename(img) for img in glob.glob(fpath_ref_images)]

# if promo is already active, moves file to already_active directory.
# if promo is new, keeps file and copies it to reference directory.
print('CHECKING NEW IMAGES...')
time.sleep(2)
for img in new_list:
    print(f'Checking new image: {img}')
    if img in active_list:
        os.replace(f'{wk_dir}/{img}', f'{fpath_already_active}/{img}')
        print('Promo already active, removing image.')
    else:
        shutil.copy(f'{wk_dir}/{img}', f'{ref_dir}/{img}')
        print('Promo is new. Copying image to reference directory.')

# if active promo is not in new_list, moves file to archive directory
# if active promo is in new_list, keeps file in reference directory
print('CHECKING ACTIVE IMAGES...')
time.sleep(2)
for img in active_list:
    print(f'Checking active image: {img}')
    if img not in new_list:
        os.replace(f'{ref_dir}/{img}', f'{ref_dir}/archive/{img}')
        ended_list.append(img)
        print('Promo no longer active, moving image to archive.')
    else:
        print('Promo is still active, keeping image.')

# saves ended_list to a CSV in the work directory for use marking end dates.
if len(ended_list) > 0:
    df = DataFrame(ended_list, columns=[f'Not Active as of {timestamp}'])
    df.to_csv(f'{wk_dir}/ended_promos {timestamp}.csv', index=False)
    print('ended_list saved to CSV.')
