# stdlib
import time
import os
import subprocess
import glob
import shutil
import argparse

# 3rd party
import pywinauto
from skimage.measure import compare_ssim
from PIL import ImageGrab
import pyautogui
import numpy
import cv2

# variable for number of times the script will
# run through multi-promo rotation
mp = 30

# directory with timestamp in name to save image files to,
# and a subdirectory to house duplicate images in
timestamp_folder = (time.strftime('%m-%d-%y'))
wk_dir = f'path/to/directory/PS4ConsoleScraper {timestamp_folder}'
ref_dir = 'path/to/directory/PS4ConsoleScraper/PS4ReferenceDirectory'
fpath_images = wk_dir + '/*.jpg'
fpath_ref_images = ref_dir + '/*.jpg'
fpath_dupes = wk_dir + '/dupes'
fpath_no_changes = wk_dir + '/no_changes'
image_dict = {}
dynamic_locations = ['ADDONS', 'FEATURE NAMED', 'FEATURED', 'FREE',
                     'GAMES big', 'GAMES eg',
                     'GAMES ft', 'PSPLUS', 'PSVR', 'STORE', 'WHATS HOT big',
                     'WHATS HOT one', 'WHATS NEW']
static_locations = ['WHATS HOT ng', 'WHATS HOT po', 'WHATS HOT nao',
                    'WHATS HOT gd', 'WHATS HOT nvr', 'DEALS one', 'DEALS gd',
                    'DEALS ppd', 'POPULAR one', 'POPULAR ts', 'POPULAR mpg',
                    'POPULAR tao', 'GAMES mp', 'GAMES oop', 'GAMES dg',
                    'GAMES npp', 'GAMES vrg', 'GAMES bs', 'GAMES npn']


# pyautogui's press function wasn't reliable
# so I made my own
def press(key):
    pyautogui.keyDown(key)
    pyautogui.keyUp(key)
    time.sleep(1)


# certain placements with videos can wonk the
# arrow-press movement process. a faster key press for those
def fast_press(key):
    pyautogui.keyDown(key)
    pyautogui.keyUp(key)
    time.sleep(.4)


# certain rotations prone to store skipping sections
def slow_press(key):
    pyautogui.keyDown(key)
    pyautogui.keyUp(key)
    time.sleep(2)


# navigates to top of nav-bar
# then moves down n times to next location
def nav_top(n, location):
    print('Navigating to top of menu')
    for i in range(10):
        fast_press('up')
    time.sleep(1)
    print(f'Navigating to {location} location')
    for i in range(n):
        press('down')
    time.sleep(2)


# navigates to bottom of nav-bar
# then moves up n times to next location
def nav_bottom(n, location):
    print('Navigating to bottom of menu')
    pyautogui.keyDown('down')
    time.sleep(7)
    pyautogui.keyUp('down')
    time.sleep(1)
    print(f'Navigating to {location} location')
    for i in range(n):
        press('up')
    time.sleep(2)


# takes a location as argument, gets a timestamp,
# takes screenshot, and saves file
def ss(location):
    print('Taking screenshot')
    # timestamp for each created image file
    timestamp_file = time.strftime('%I%M%S', time.localtime())
    ImageGrab.grab().save(f'{wk_dir}/{location} {timestamp_file}.jpg', 'JPEG')
    time.sleep(1)


# makes sure ps4 remote play is foreground window
def set_fg():
    wnd = pywinauto.findwindows.find_window(title='PS4 Remote Play')
    pywinauto.win32functions.SetForegroundWindow(wnd)
    time.sleep(2)


# recalibrates every 10 passes, in case the scraper taking screenshots
# of the improper spot. backs out to main screen and navigates back to the
# right location
def recalibrate(location):
    print('Recalibrating, please stand by...')
    for i in range(5):
        press('esc')
    for i in range(10):
        fast_press('up')
    press('down')
    pyautogui.keyDown('left')
    time.sleep(5)
    pyautogui.keyUp('left')

    # different logic for nagivating to various locations
    if location == 'STORE':
        pass
    elif location == 'FEATURED':
        press('enter')
        time.sleep(5)
    else:
        press('enter')
        time.sleep(5)
        nav_bottom(n, location)


# takes a location as an argument, removes all duplicate images
# with that location keyword in the filename, and puts them into
# a dupes folder
def dupe_remover(location):
    # loads in grayscale versions of the images in the directory,
    # appends each image to a list, then appends the
    # filepath base name to a matching list
    # for later use moving the file if it's a dupe
    for img in glob.glob(fpath_images):
        imname = os.path.basename(img)
        # only loads in images if they are in the specified section
        if location in imname:
            image = cv2.imread(img, 0)
            image_dict[imname] = image
        else:
            pass

    unique_images = {}
    duplicate_images = {}
    while len(image_dict) > 0:

        # grab the first image
        # and comapre it against every other image we have
        image_name = list(image_dict.keys())[0]
        image = image_dict[image_name]

        duplicate_to_this_image = []
        for other_image_name, other_image in image_dict.items():
            if image_name == other_image_name:
                continue

            # if the image is a duplicate, move it to the dupes folder
            # and remove it from the image dictionary
            ssim = compare_ssim(image, other_image)
            print(f'{image_name} to {other_image_name} SSIM: {ssim}')
            if ssim > .97:
                print('Moving dupe')
                os.rename(f'{wk_dir}/{other_image_name}',
                          f'{fpath_dupes}/{other_image_name}')
                duplicate_to_this_image.append(other_image_name)

        for dupe_name in duplicate_to_this_image:
            dupe_image = image_dict[dupe_name]
            del image_dict[dupe_name]
            duplicate_images[dupe_name] = dupe_image

        # Now that we've compared the image
        # It should be considered unique
        unique_images[image_name] = image
        del image_dict[image_name]


def new_image_check(location):
    ''' checks each captured location against a reference image directory.
    loads images and compares SSIM using cv2.
    if the images are the same, the just-captured image is moved to
    "no changes" directory. if the images are different, the just-captured
    image is copied and replaces the image in the ref directory.
    '''

    image_list = []
    print(f'Checking {location} location.')
    for img in glob.glob(fpath_images):
        imname = os.path.basename(img)
        if location in imname:
            image = cv2.imread(img, 0)
            image_name = os.path.basename(img)
            image_list.append(image)
            print(f'Image: {image_name}')
        else:
            pass

    for ref_img in glob.glob(fpath_ref_images):
        ref_imname = os.path.basename(ref_img)
        if location in ref_imname:
            ref_image = cv2.imread(ref_img, 0)
            ref_image_name = os.path.basename(ref_img)
            image_list.append(ref_image)
            print(f'Ref image: {ref_image_name}')
        else:
            pass

    # resizes images if they are not the same resolution,
    # since SSIM needs same-sized images to compare
    if image.size != ref_image.size:
        print('Resizing images...')
        image = cv2.resize(image, (1920, 1080))
        ref_image = cv2.resize(ref_image, (1920, 1080))
    else:
        pass

    # makes sure there are 2 images to compare. if not, skips.
    if len(image_list) > 1:

        # compares the 2 images
        ssim = compare_ssim(image, ref_image)
        print(f'SSIM: {ssim}')
        if ssim > .95:
            print('New image is the same as reference image. No changes.')
            os.rename(f'{wk_dir}/{image_name}',
                      f'{fpath_no_changes}/{image_name}')
        else:
            print('New image is different. Updating image in reference'
                  'directory and moving old image to "archive" directory.')
            try:
                os.rename(f'{ref_dir}/{ref_image_name}',
                          f'{ref_dir}/archive/{ref_image_name}')

            # overwrites the file if a same-name file already exists
            except OSError:
                os.replace(f'{ref_dir}/{ref_image_name}',
                           f'{ref_dir}/archive/{ref_image_name}')
            shutil.copy(f'{wk_dir}/{image_name}', f'{ref_dir}/{image_name}')
    else:
        print("Something went wrong, there aren't two images to comapre."
              "Moving to next location.")


def setup():
    os.makedirs(wk_dir, exist_ok=True)
    os.makedirs(fpath_dupes, exist_ok=True)
    os.makedirs(fpath_no_changes, exist_ok=True)
    # Opens the ps4 remote play program
    print('Opening remote play, one moment please...')
    subprocess.Popen('C:/Users/NAME/PS4ConsoleScraper/RemotePlay/'
                     'RemotePlay.exe')
    time.sleep(10)
    set_fg()
    press('tab')
    press('enter')
    print('Waiting 90 seconds for PS4 to turn on...')
    time.sleep(30)
    # print('60 more seconds...')
    # time.sleep(30)
    # print('30 more seconds...')
    # time.sleep(30)
    set_fg()
    pyautogui.hotkey('alt', 'enter')


def cap_wn():
    location = 'WHATS NEW'
    print(f'Navigating to {location} location')
    # goes through each promotion in the location
    # and takes a screenshot
    # put in a couple redundant moves to be safe
    # this location can have varying promo numbers
    for i in range(10):
        fast_press('down')
        ss(location)


def cap_store():
    location = 'STORE'
    recal = 1
    print(f'Navigating to {location} location')
    press('esc')
    time.sleep(1)
    press('left')
    # toggles back and forth variable number of times to grab all promos
    for i in range(mp):
        print(f'Pass {i+1} of {mp}')
        time.sleep(2)
        for i in range(3):
            fast_press('down')
        ss(location)
        press('esc')
        press('right')
        time.sleep(1)
        press('left')
        recal += 1
        if recal > 10:
            recal = 1
            recalibrate(location)


def cap_feat_wh():
    recal = 1
    location = 'FEATURED'
    print(f'Navigating to {location} location')
    press('enter')
    time.sleep(8)
    print(f'Executing multi-promo placement rotation')
    # toggles back and forth variable number of times to grab all promos
    for i in range(mp):
        print(f'Pass {i+1} of {mp}')
        fast_press('right')
        fast_press('up')
        ss(location)
        fast_press('down')
        press('left')
        location = 'WHATS HOT'
        print(f'Navigating to {location} location')
        for i in range(5):
            fast_press('up')
        press('down')
        press('down')
        time.sleep(2)
        press('right')
        ss(f'{location} one')
        for i in range(6):
            press('right')
        fast_press('right')
        press('up')
        ss(f'{location} big')
        fast_press('down')
        press('left')
        press('esc')
        location = 'FEATURED'
        print(f'Navigating back to {location} location')
        time.sleep(1)
        press('up')
        time.sleep(2)
        recal += 1
        if recal > 10:
            recal = 1
            recalibrate(location)


def cap_wh():
    location = 'WHATS HOT'
    n = 2
    nav_top(n, location)
    print(f'Executing main {location} rotation')
    press('right')
    ss(f'{location} one')
    for i in range(3):
        press('right')
    ss(f'{location} po')
    for i in range(3):
        press('right')
    fast_press('right')
    press('up')
    ss(f'{location} big')
    fast_press('down')
    press('right')
    ss(f'{location} ng')
    for i in range(4):
        press('right')
    ss(f'{location} nao')
    press('right')
    press('right')
    ss(f'{location} gd')
    for i in range(4):
        press('right')
    ss(f'{location} nvr')
    press('esc')


def cap_deals():
    location = 'DEALS'
    n = 3
    nav_top(n, location)
    press('right')
    ss(f'{location} one')
    for i in range(4):
        press('right')
    ss(f'{location} gd')
    for i in range(3):
        press('right')
    ss(f'{location} ppd')
    press('esc')


def cap_pop():
    location = 'POPULAR'
    n = 4
    nav_top(n, location)
    press('right')
    ss(f'{location} one')
    for i in range(4):
        press('right')
    ss(f'{location} ts')
    for i in range(3):
        press('right')
    ss(f'{location} mpg')
    for i in range(3):
        press('right')
    ss(f'{location} tao')
    press('esc')


def cap_branded():
    location = 'BRANDED'
    n = 6
    nav_top(n, location)
    # put in a couple redundant moves to be safe
    # since this location can have varying promo numbers
    for i in range(4):
        location = f'BRANDED {i+1}'
        fast_press('right')
        fast_press('up')
        press('up')
        ss(location)
        press('down')
        press('down')
        # tries to go to the right, in case the promo has
        # multiple pages
        for i in range(7):
            fast_press('right')
            ss(location)
        press('esc')
        press('left')
        press('down')
        time.sleep(2)


def cap_free():
    location = 'FREE'
    n = 9
    recal = 1
    nav_bottom(n, location)
    print(f'Executing multi-promo placement rotation')
    for i in range(mp):
        print(f'Pass {i+1} of {mp}')
        press('right')
        press('right')
        ss(location)
        press('left')
        press('left')
        slow_press('up')
        slow_press('down')
        recal += 1
        if recal > 10:
            recal = 1
            recalibrate(location)


def cap_addons():
    location = 'ADDONS'
    n = 12
    recal = 1
    nav_bottom(n, location)
    print(f'Executing multi-promo placement rotation')
    for i in range(mp):
        print(f'Pass {i+1} of {mp}')
        press('right')
        press('right')
        ss(location)
        press('left')
        press('left')
        slow_press('up')
        slow_press('down')
        recal += 1
        if recal > 10:
            recal = 1
            recalibrate(location)


def cap_vr_plus():
    location = 'PSVR'
    n = 14
    recal = 1
    nav_bottom(n, location)
    print(f'Executing multi-promo placement rotation')
    for i in range(mp):
        print(f'Pass {i+1} of {mp}')
        press('right')
        press('right')
        ss(location)
        press('left')
        press('left')
        location = 'PSPLUS'
        print(f'Navigating to {location} location.')
        slow_press('up')
        ss(location)
        location = 'PSVR'
        print(f'Navigating back to {location} location.')
        slow_press('down')
        recal += 1
        if recal > 10:
            recal = 1
            recalibrate(location)


def cap_games_rot():
    location = 'GAMES'
    n = 13
    recal = 1
    nav_bottom(n, location)
    press('right')
    for i in range(mp):
        print(f'Pass {i+1} of {mp}')
        press('right')
        ss(f'{location} eg')
        for i in range(9):
            press('right')
        fast_press('right')
        press('up')
        ss(f'{location} big')
        fast_press('down')
        press('left')
        press('esc')
        press('down')
        time.sleep(2)
        fast_press('right')
        press('up')
        ss(f'{location} ft')
        fast_press('down')
        press('left')
        press('up')
        time.sleep(2)
        recal += 1
        if recal > 10:
            recal = 1
            recalibrate(location)
            press('right')
    press('left')
    press('left')


def cap_games_main():
    location = 'GAMES'
    n = 13
    nav_bottom(n, location)
    press('right')
    press('right')
    ss(f'{location} eg')
    for i in range(3):
        press('right')
    ss(f'{location} mp')
    for i in range(4):
        press('right')
    ss(f'{location} oop')
    for i in range(2):
        press('right')
    fast_press('right')
    press('up')
    ss(f'{location} big')
    fast_press('down')
    press('right')
    ss(f'{location} dg')
    for i in range(4):
        press('right')
    ss(f'{location} npp')
    press('right')
    press('right')
    ss(f'{location} vrg')
    for i in range(4):
        press('right')
    ss(f'{location} bs')
    for i in range(4):
        press('right')
    ss(f'{location} npn')
    press('esc')
    press('left')


def restart():
    print('Restarting the PS4')
    for i in range(5):
        press('esc')
    time.sleep(5)
    press('up')
    for i in range(15):
        press('right')
    press('enter')
    press('down')
    press('enter')
    press('down')
    press('down')
    press('enter')
    time.sleep(2)
    print('Closing PS4 Remote Play App...')
    pyautogui.hotkey('alt', 'f4')
    time.sleep(2)


# Runs the full scraper (done once a day)
def capture_full():
    print('RUNNING FULL SCRAPE')
    setup()
    cap_wn()
    cap_store()
    cap_feat_wh()
    cap_wh()
    cap_deals()
    cap_pop()
    cap_branded()
    cap_free()
    cap_addons()
    cap_vr_plus()
    cap_games_rot()
    cap_games_main()
    restart()
    for location in dynamic_locations:
        print(f'Removing dupes from {location}.')
        dupe_remover(location)
    shutil.rmtree(fpath_dupes)
    for location in static_locations:
        new_image_check(location)


# Runs through the rotational locations only (done twice a day)
def capture_rotations():
    print('RUNNING ROTATIONAL SCRAPE')
    setup()
    cap_store()
    cap_feat_wh()
    cap_free()
    cap_addons()
    cap_vr_plus()
    cap_games_rot()
    restart()
    for location in dynamic_locations:
        print(f'Removing dupes from {location}.')
        dupe_remover(location)
    shutil.rmtree(fpath_dupes)


# Take in arguments to run through full scrape or rotational-only scrape
# and execute
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()
parser_full = subparsers.add_parser('full', help='Runs the full scrape.')
parser_full.set_defaults(func=capture_full)
parser_rotation = subparsers.add_parser('rotation',
                                        help='Runs only through the rotating'
                                        'locations.')
parser_rotation.set_defaults(func=capture_rotations)
parse_it = parser.parse_args()
parse_it.func()
