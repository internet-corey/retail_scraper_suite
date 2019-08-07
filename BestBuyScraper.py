# stdlib
import time
import glob
import os
import shutil
import string
import base64
import json

# 3rd party
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import pandas as pd
from PIL import Image
from skimage.measure import compare_ssim
import numpy
import cv2


def start_chromedriver():
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome("chromedriver.exe", options=options)
    driver.set_page_load_timeout(60)
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
                    .replace('.', '').replace('!', '')).replace('\n', '')
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


def name_reducer(name_raw):
    '''If the element name is greater than 100 characters, truncates it to max
    100 chars, so that the final full file name will not exceed the OS char
    limit.'''
    if len(name_raw) > 100:
        diff = len(name_raw) - 100
        name_raw = name_raw[:-diff]
    return name_raw


def new_image_check(location):
    '''checks filenames to see if images in scrape results are new or existing.
    if existing, they are removed. checks reference images and deletes if they
    are not in scrape results (meaning they are no longer active on the store).
    does an additional SSIM comparison for carousel images since names can be
    the same but with different image / metadata.
    '''
    new_list = []
    active_list = []
    print(f'Checking {location}')
    for img in glob.glob(fpath_images):
        image = os.path.basename(img)
        if location in image:
            new_list.append(image)

    for img in glob.glob(fpath_ref_images):
        ref_image = os.path.basename(img)
        if location in ref_image:
            active_list.append(ref_image)

    # if promo is already active, moves file to active directory.
    # if promo is new, keeps file and copies it to reference directory.
    # does an extra SSIM check for carousel promos.
    print('Checking new images.')
    for img in new_list:
        print(f'Checking new image: {img}')
        if img in active_list:
            if 'web main small' in img or 'web deals' in img:
                os.rename(f'{wk_dir}/{img}', f'{fpath_active}/{img}')
                print('Promo already active, removing image.')

            # carousel promo
            else:
                im = cv2.imread(f'{wk_dir}/{img}', 0)
                refim = cv2.imread(f'{ref_dir}/{img}', 0)

                # different crop coords based on location
                if 'web main slide' in img:
                    im2 = im[main_y1:main_y2, main_x1:main_x2].copy()
                    refim2 = refim[main_y1:main_y2, main_x1:main_x2].copy()
                else:
                    im2 = im[y1:y2, x1:x2].copy()
                    refim2 = refim[y1:y2, x1:x2].copy()

                # SSIM needs same size to compare. makes sizes same if not
                if im2.size != refim2.size:
                    im2 = (cv2.resize(im2, (refim2.shape[1],
                           refim2.shape[0])))

                # compares the 2 images
                ssim = compare_ssim(im2, refim2)
                if ssim > .97:
                    os.rename(f'{wk_dir}/{img}', f'{fpath_active}/{img}')
                    print('Promo already active, removing image.')
                else:
                    try:
                        os.rename(f'{ref_dir}/{img}',
                                  f'{ref_dir}/archive/{img}')
                    except OSError:
                        os.replace(f'{ref_dir}/{img}',
                                   f'{ref_dir}/archive/{img}')
                    active_list.remove(img)
                    ended_list.append(img)
                    shutil.copy(f'{wk_dir}/{img}', f'{ref_dir}/{img}')
                    print('Promo is new. Updating image in ref directory.')

        else:
            shutil.copy(f'{wk_dir}/{img}', f'{ref_dir}/{img}')
            print('Promo is new. Copying image to ref directory.')

    # if active promo is not in new_list, moves file to archive directory
    # if active promo is in new_list, keeps file in reference directory
    print('Checking active images.')
    for img in active_list:
        print(f'Checking active image: {img}')
        if img not in new_list:
            try:
                os.rename(f'{ref_dir}/{img}', f'{ref_dir}/archive/{img}')
            except OSError:
                os.replace(f'{ref_dir}/{img}', f'{ref_dir}/archive/{img}')
            ended_list.append(img)
            print('Promo no longer active, moving image to archive.')
        else:
            print('Promo is still active, keeping image.')


url_dict = {'web main': 'https://www.bestbuy.com/',
            'web games': ('https://www.bestbuy.com/site/electronics/'
                          'video-games/abcat0700000.c?id=abcat0700000'),
            'web xb1': ('https://www.bestbuy.com/site/video-games/xbox-one/'
                        'pcmcat300300050002.c?id=pcmcat300300050002'),
            'web ps4': ('https://www.bestbuy.com/site/video-games/playstation-'
                        '4-ps4/pcmcat295700050012.c?id=pcmcat295700050012'),
            'web ns': ('https://www.bestbuy.com/site/video-games/nintendo-'
                       'switch/pcmcat1476977522176.c?id=pcmcat1476977522176'),
            'web deals': ('https://www.bestbuy.com/site/featured-offers/video-'
                          'game-toy-sale/pcmcat8400050004.c?id='
                          'pcmcat8400050004')
            }
ended_list = []

# Creates directories for the day.
timestamp = (time.strftime('%m-%d-%y', time.localtime()))
timestamp_folder = (time.strftime('%m-%d-%y--%I-%M %p', time.localtime()))
wk_dir = (f'//cammy.eedar.com/vol1/Retail Research/Z Automation Results/'
          f'BestBuyScraper/BestBuyScraper {timestamp_folder}')
ref_dir = (f'//cammy.eedar.com/vol1/Retail Research/Z Automation Results/'
           f'BestBuyScraper/BestBuyReferenceDirectory')
fpath_images = wk_dir + '/*.png'
fpath_ref_images = ref_dir + '/*.png'
fpath_active = wk_dir + '/active'
fpath_archive = ref_dir + '/archive'

# main page crop coordinates for SSIM comparison
main_y1 = 150
main_y2 = 540
main_x1 = 0
main_x2 = 1920

# games / console page crop coordinates for SSIM comparison
y1 = 275
y2 = 580
x1 = 0
x2 = 1120

os.makedirs(wk_dir, exist_ok=True)
os.makedirs(ref_dir, exist_ok=True)
os.makedirs(fpath_active, exist_ok=True)
os.makedirs(fpath_archive, exist_ok=True)


# loops through each URL and captures promos
driver = start_chromedriver()
for url in url_dict:
    driver.get(url_dict[url])
    time.sleep(3)

    # removes a top-bar ad
    try:
        js = ('var aa=document.getElementsByClassName("media-network-ad")[0];'
              'aa.parentNode.removeChild(aa)')
        driver.execute_script(js)
        time.sleep(1)
    except NoSuchElementException:
        pass

    if url == 'web main':

        # deletes a 'pop up' element that covers the main page
        popup = driver.find_element_by_class_name('email-submission-modal')
        close_it = popup.find_element_by_css_selector('button.close')
        close_it.click()
        time.sleep(1)
        print(f'scraping {url}')

        # sets a pixel value to crop the image
        cutoff = (driver.find_element_by_class_name('widget-recommendations')
                  .location['y'])

        # carousel
        i = 0
        slides = driver.find_element_by_class_name('widget-primary-message')
        buttons = slides.find_elements_by_xpath('.//button[contains(@class,'
                                                '"dot")]')
        for button in buttons:
            buttons[i+2].click()
            time.sleep(2)
            try:
                box = slides.find_element_by_id(f'pm-panel-{i+2}')
                name_raw = box.find_element_by_class_name('pm-headline').text
                name = filter_chars(name_raw)
                name = name_reducer(name)
            except NoSuchElementException:
                name = f'Image {i+2}'
            file_name = f'{wk_dir}/{url} slide - {name} - promo.png'

            # takes a full-page screenshot and crops
            fp_ss(driver=driver, image=file_name)
            time.sleep(1)
            cropped = Image.open(file_name)
            cropped = cropped.crop((0, 0, cropped.width, cutoff))
            cropped.save(file_name)
            print(name)
            time.sleep(.5)
            i -= 1

        # promo grid
        fixed = driver.find_elements_by_class_name('container-col')
        fixed_image = f'{wk_dir}/fixed_image.png'

        # takes a screenshot and crops
        fp_ss(driver=driver, image=fixed_image)
        cropped = Image.open(fixed_image)
        cropped = cropped.crop((0, 0, cropped.width, cutoff))
        cropped.save(fixed_image)

        # gets each promo's element name and copies fixed image with promo's
        # file name
        for promo in fixed:
            name_raw = promo.find_element_by_class_name('undefined').text
            name = filter_chars(name_raw)
            name = name_reducer(name)
            file_name = f'{wk_dir}/{url} small - {name} - promo.png'
            shutil.copy(fixed_image, file_name)
            print(name)
            time.sleep(.2)
        os.remove(fixed_image)

    elif url == 'web deals':
        print(f'scraping {url}')
        promos = driver.find_elements_by_class_name('offer-column')
        cutoff = driver.find_element_by_class_name('widget-flex').location['y']
        deals_image = f'{wk_dir}/deals_image.png'

        # taes a screenshot and crops
        fp_ss(driver=driver, image=deals_image)
        cropped = Image.open(deals_image)
        cropped = cropped.crop((0, 0, cropped.width, cutoff))
        cropped.save(deals_image)

        # gets each promo's element name and copies fixed image with promo's
        # file name
        for promo in promos:
            name_raw = promo.find_element_by_class_name('offer-link').text
            name = filter_chars(name_raw)
            name = name_reducer(name)
            ptype = promo.find_element_by_class_name('browse-button').text
            if ptype == 'Pre-Order':
                promotype = 'preorder'
            else:
                promotype = 'promo'
            file_name = f'{wk_dir}/{url} - {name} - {promotype}.png'
            print(name)
            shutil.copy(deals_image, file_name)
            time.sleep(.2)
        os.remove(deals_image)

    # the games and console pages
    else:
        i = 0
        print(f'scraping {url}')
        promos = driver.find_elements_by_class_name('rotating-panel-item')
        for promo in promos:
            button = promo.find_element_by_id(f'pm-button-{i}')
            button.click()
            time.sleep(1)
            name_raw = promo.find_element_by_class_name('cell-title').text
            name = filter_chars(name_raw)
            name = name_reducer(name)
            file_name = f'{wk_dir}/{url} - {name} - promo.png'
            driver.save_screenshot(file_name)
            print(name)
            time.sleep(.5)
            i += 1

driver.close()

for location in url_dict:
    new_image_check(location)

# saves ended_list (if it exists) to a CSV in the work directory
# for use marking end dates.
if len(ended_list) > 0:
    df = pd.DataFrame(ended_list, columns=['No Longer Active'])
    df.to_csv(f'{wk_dir}/ended_promos {timestamp}.csv', index=False)
    print('ended_list saved to CSV.')
