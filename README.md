# Scrapers for Videogame Retailers

## Installation
PS4 Remote Play app needed for PS4 scraper.
```
https://remoteplay.dl.playstation.net/remoteplay/lang/en/index.html
```
Imports
```
$ pip install -r requirements.txt
```

## Overview

### Walmart Scraper
- Takes screenshots of videogame advertisements on main page, videogames page, and console (xb1, ps4, switch) pages of walmart.com
- Saves image file with metadata generated from selenium-pulled web elements
- Checks saved files against a reference directory (comparing filepaths) to only keep new ads, and also create a CSV for ads which are no longer present.

### PS4 Scraper
- Connects to a PS4 via the Remote Play app.
- Uses command line arguments to run through the full scrape, or only to scrape the locations with a rotating carousel.
- Takes screenshots of videogame advertisements across the various console storefront pages.
- Saves image file with naming convention.
- Goes through locations with carousel images variable number of times, usually around 50, to grab all possible ads, since only 1 in the carousel is visible at any given moment.
- Uses SSIM comparison to check saved images against a reference directory, in order to discard images of locations that have no new ads, and only show locations that have changed, IE have 1 or more different advertisements.
- Uses SSIM comparison to remove duplicates of the carousel placements. 

### Best Buy Scraper
- Takes screenshots of videogame advertisements on main page, videogames page, and console (xb1, ps4, switch) pages of bestbuy.com
- Saves image file with metadata generated from selenium-pulled web elements
- Checks saved files against a reference directory to only keep new ads. Does filename comparisons and also SSIM comparisons for carousel images. Creates a CSV for ads which are no longer present.

### Gmail Scraper
- Connects to gmail account with imaplib
- Pulls metadata such as thread ID sender, date, subject line, from imap. Saves metadata to CSV.
- Uses thread ID and selenium to go directly to email's webpage and takes a screenshot. 
