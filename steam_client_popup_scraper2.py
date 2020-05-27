'''takes screenshots of ads in the Steam PC client's Update News section
'''

# stdlib
import time
import subprocess
import os
from glob import glob
import argparse

# 3rd party
import cv2
import numpy as np
import pyautogui
import win32gui
from PIL import Image, ImageGrab
from imagehash import phash


def get_handles(handles=[]):
    '''returns list of handles for visible window
    '''
    def window_enum_handler(hwnd, resultList):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) != '':
            resultList.append((hwnd, win32gui.GetWindowText(hwnd)))

    mlst = []
    win32gui.EnumWindows(window_enum_handler, handles)
    for handle in handles:
        mlst.append(handle)
    return mlst


def set_fg(name=None, hndl=None):
    '''
    sets foreground window for windows handle, or searches by name then sets
    args - name: str - windows handle name.
    args - hndl: str - windows handle
    '''
    if name:
        hndl = win32gui.FindWindow(None, name)
    if hndl:
        win32gui.SetForegroundWindow(hndl)
    time.sleep(1)


def find_template(tmp, clicks=True):
    '''takes screenshot, finds coords of tmp arg within screenshot, moves to
    coords on screen, clicks if clicks=True.
    args - tmp: str - jpeg image filepath.
    args - clicks: bool - clicks at template match coords if true, not if false
    '''

    # takes screenshot using PIL ImageGrab, converts to cv2 image
    ss = ImageGrab.grab()
    ss_cv2 = cv2.cvtColor(
        np.array(ss),
        cv2.COLOR_RGB2BGR
    )

    # loads cv2 image of template to match on, then matches
    template = cv2.imread(tmp)
    match = cv2.matchTemplate(
        ss_cv2,
        template,
        cv2.TM_CCOEFF_NORMED
    )

    # gets x, y coords of template's location within img,
    # moves to location and clicks
    match_y, match_x = np.unravel_index(
        match.argmax(),
        match.shape
    )
    pyautogui.moveTo(
        x=match_x,
        y=match_y,
        duration=0.3
    )
    time.sleep(.5)
    if clicks:
        pyautogui.click()
        time.sleep(1)


def close_initial_new_ads(close_jpg):
    '''looks for the "Steam - News" window if it auto-opens when opening steam
    client, then closes, since initial ads are only new ones, not the total.
    '''
    handle_list = get_handles()
    for i in handle_list:
        handle, name = i
        if 'Steam - News' in name:
            print('closing window of only new ads')
            find_template(close_jpg)


def get_total_ads():
    '''finds total ads in the "Steam - News" window based on window name,
    (Steam - News (1 of x)), returns int(x)
    '''
    handle_list = get_handles()
    for i in handle_list:
        handle, name = i
        if 'Steam - News' in name:
            bbox = win32gui.GetWindowRect(handle)
            discard, total = name.split('of ')
            set_fg(hndl=handle)
            total = int(total[:-1])
            tup = (handle, bbox, total)
            return tup
            break


def dupe_remover(wd):
    '''
    Checks jpegs in wd for dupes
    args - wd: str - a directory
    '''
    print(f'removing dupes')
    image_dict = {}
    unique_images = {}
    duplicate_images = {}
    image_files = f'{wd}/*.jpg'

    for img in glob(image_files):
        imname = os.path.basename(img)
        image = Image.open(img).convert('L')
        image_dict[imname] = image

    while len(image_dict) > 0:

        # grab the first image
        # and comapre it against every other image we have
        image_name = list(image_dict.keys())[0]
        image = image_dict[image_name]
        duplicate_to_this_image = []
        for other_image_name, other_image in image_dict.items():
            if image_name == other_image_name:
                continue

            # if the image is a duplicate, remove it from the image dictionary
            # and delete the file
            p = phash(image)
            p_other = phash(other_image)
            delta = p - p_other
            if delta < 7:
                other_file = f'{wd}/{other_image_name}'
                os.remove(other_file)
                duplicate_to_this_image.append(other_image_name)

        for dupe_name in duplicate_to_this_image:
            dupe_image = image_dict[dupe_name]
            del image_dict[dupe_name]
            duplicate_images[dupe_name] = dupe_image

        # Now that we've compared the image
        # It should be considered unique
        unique_images[image_name] = image
        del image_dict[image_name]


def scrape_popups(wd):
    '''opens steam client, navigates to and scrapes ads from update news
    section.
    args - wd: str - file directory to save screenshots to
    '''

    # vars
    steam_client = 'filepath\\steam.exe'
    assets_dir = 'filepath_2\\assets'
    view_jpg = f'{assets_dir}\\view_btn.jpg'
    update_news_jpg = f'{assets_dir}\\update_news_btn.jpg'
    next_jpg = f'{assets_dir}\\next_btn.jpg'
    close_jpg = f'{assets_dir}\\close_btn.jpg'

    # opens up steam client
    print('opening steam client')
    steam = subprocess.Popen(steam_client)
    time.sleep(10)
    set_fg(name='Steam')
    close_initial_new_ads(close_jpg)
    print('opening update news')

    # find and click view button in steam client
    find_template(view_jpg)

    # find and click update news button within view menu
    find_template(update_news_jpg)
    time.sleep(5)

    # gets handle name, int of total ads, and bounding box of news window
    news_hndl, bbox, total = get_total_ads()

    # moves to next button within news window
    print('grabbing screenshots of each ad')
    find_template(next_jpg, clicks=False)

    # screenshots all ads per total int, then removes dupes
    for i in range(total):
        promoname = f'popup_{i+1}'
        promo_fpath = f'{wd}\\{promoname}.jpg'
        set_fg(hndl=news_hndl)
        ImageGrab.grab(bbox).save(promo_fpath, 'JPEG')
        pyautogui.click()
    find_template(close_jpg)
    steam.kill()
    dupe_remover(wd)
    print('done')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'directory',
        action='store',
        help='''runs scrape_popups fuction. arg is directory where screenshots
        are saved'''
    )
    args = parser.parse_args()

    if os.path.isdir(args.directory):
        scrape_popups(args.directory)
    else:
        print('Error. Given argument is not a directory.')
