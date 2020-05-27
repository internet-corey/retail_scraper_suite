# Scrapers for Videogame Retailers

## Installation
Imports
```
$ pip install -r requirements.txt
```

## Overview

These are not all of the scrapers I have built, but a few examples from each retailer type (website, email account, console storefront, PC storefront).
PS4 now has its own repo because of enhancements that split it out into multiple .py files.

### Walmart Scraper
- Takes screenshots of videogame advertisements on main page, videogames page, and console (xb1, ps4, switch) pages of walmart.com
- Saves image file with metadata generated from selenium-pulled web elements
- Checks saved files against a reference directory (comparing filepaths) to only keep new ads, and also create a CSV for ads which are no longer present.

### PS4 Scraper
- Moved PS4 scraper to its own repo: https://github.com/internet-corey/ps4_scraper 

### Best Buy Scraper
- Takes screenshots of videogame advertisements on main page, videogames page, and console (xb1, ps4, switch) pages of bestbuy.com
- Saves image file with metadata generated from selenium-pulled web elements
- Checks saved files against a reference directory to only keep new ads. Does filename comparisons and also SSIM comparisons for carousel images. Creates a CSV for ads which are no longer present.

### Gmail Scraper
- Connects to gmail account with imaplib
- Pulls metadata such as thread ID sender, date, subject line, from imap. Saves metadata to CSV.
- Uses thread ID and selenium to go directly to email's webpage and takes a screenshot.

### Steam Popup Scraper
- Opens Steam PC client
- Uses OpenCV template matching to find and click buttons based on saved template jpg's
- Saves screenshots to argparsed directory
