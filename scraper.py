import time
import re
import csv
import json
import os
import random
from videogame import VideoGame
from selenium import webdriver
from bs4 import BeautifulSoup
from datetime import datetime

#TODO support TROUBLE_CONSOLES_MARIONETTE and TROUBLE_CONSOLES_KILL
#TODO add support for browsers other than firefox in scrollBottom()
#TODO add compression for csv file, convert the three doubles into one value

# console names as they appear in pricecharting.com URLs
CONSOLES = ["sega-game-gear", "gamecube", "wii-u", "sega-dreamcast", "playstation-vita"]
#CONSOLES = ["super-nintendo", "nes", "nintendo-64", "gamecube", "wii", "wii-u", "nintendo-switch", "gameboy",
#        "gameboy-advance", "nintendo-ds", "virtual-boy", "game-&-watch", "playstation", "playstation-2", "playstation-3",
#        "playstation-4", "sega-master-system", "sega-genesis", "sega-32x", "sega-saturn",
#        "sega-dreamcast", "sega-game-gear", "xbox", "xbox-360", "xbox-one", "atari-2600", "atari-5200"]

# produce exception "Failed to decode response from marionette" in main()
TROUBLE_CONSOLES_MARIONETTE = ["psp", "nintendo-3ds", "atari-7800", "jaguar"]

# produce exception "invalid argument: can't kill an exited process" in main()
TROUBLE_CONSOLES_KILL = ["sega-cd", "gameboy-color", "playstation-vita", "atari-lynx"]

def gameCsv(games):
    """Creates csv file to store our scraped data

    Args:
        games: (list of videogame objects) videogame data scraped in our program
    """
    dt = datetime.now().strftime("%d.%m.%Y_%H.%M.%S")
    fn = "game_prices.csv"
    if not os.path.exists(dt):
        os.mkdir(dt)
    with open(os.path.join(dt, fn), 'w') as csv_file:
        fieldnames = ['game', 'console', 'loose_val', 'complete_val', 'new_val', 'date(D/M/Y)']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for g in games:
            writer.writerow({'game': g.getTitle(), 'console': g.getConsole(), 'loose_val': g.getLoosePrice(), 'complete_val': g.getCompletePrice(),
            'new_val': g.getNewPrice(), 'date(D/M/Y)': dt.split('_')[0].replace('.', '/')})

    # create a copy as 'output-latest'
    latest_dir = "output-latest"
    if not os.path.exists(latest_dir):
        os.mkdir(latest_dir)
    import shutil
    shutil.copy2(os.path.join(dt, fn), os.path.join(latest_dir, fn))

    # write manifest.json
    manifest_path = os.path.join(latest_dir, 'manifest.json')
    with open(manifest_path, 'w') as manifest_file:
        json.dump({"datestamp": dt}, manifest_file, indent=4)


def scrollBottom(console):
    """Scrolls to the bottom of webpage. pricecharting.com/console/<console-name> loads x number of videogames at a time, this loads all
        videogames for our console before we scrape values

    Args:
        console: (string) game system name as it appears in the pricecharting URL

    Returns:
        (browser) html for webpage with all values loaded
    """
    SCROLL_PAUSE_TIME = 1
    browser = webdriver.Firefox()

    browser.get('https://www.pricecharting.com/console/' + console + '?sort=name')
    prevHeight = browser.execute_script("return document.body.scrollHeight")
    atBottom = False # occasionally selenium lags, this ensures that we are truly at the bottom
    while True:
        time.sleep(SCROLL_PAUSE_TIME)
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        currHeight = browser.execute_script("return document.body.scrollHeight")
        if prevHeight == currHeight:
            if atBottom:
                break
            atBottom = True
        else:
            atBottom = False
        prevHeight = currHeight

    return browser


def scrapeVals(console, browser):
    """Scrapes titles and values for each videogame in our webpage

    Args:
        console: (string) game system name as it appears in the pricecharting URL
        browser: (browser) html for webpage with all values loaded

    Returns:
        (list) videogame objects for our console
    """
    games = []
    soup = BeautifulSoup(browser.page_source, 'html.parser')
    for EachPart in soup.select('tr[id*="product-"]'):
        title = re.search(r'>(.*?)</a>', str(EachPart.select('td[class="title"]'))).group(1)
        loosePrice = re.findall(r"\d+\.\d+", str(EachPart.select('td[class="price numeric used_price"]')))
        loosePrice = loosePrice[0] if len(loosePrice) > 0 else "N/A"
        completePrice = re.findall(r"\d+\.\d+", str(EachPart.select('td[class="price numeric cib_price"]')))
        completePrice = completePrice[0] if len(completePrice) > 0 else "N/A"
        newPrice = re.findall(r"\d+\.\d+", str(EachPart.select('td[class="price numeric new_price"]')))
        newPrice = newPrice[0] if len(newPrice) > 0 else "N/A"
        newGame = VideoGame(title, console, loosePrice, completePrice, newPrice)
        games.append(newGame)
    return games


def pullVals(console):
    """Pulls values from pricecharting.com

    Args:
        console: (string) game system name as it appears in the pricecharting URL

    Returns:
        (list) videogame objects
    """
    print ('Pulling values for %s console\n' % (console))
    browser = None
    try:
        browser = scrollBottom(console)
        return scrapeVals(console, browser)
    finally:
        if browser is not None:
            browser.quit()


def main():
    """Orders execution of our program: scrape vals for each console then create CSV file
    """
    allGames = []
    for i, console in enumerate(CONSOLES):
        scrapedConsoleGames = []
        max_retries = 3
        for attempt in range(max_retries):
            try:
                consoleGames = pullVals(console)
                if len(consoleGames) < 25:
                    raise ValueError("Scraped only %d games, expected at least 25." % len(consoleGames))
                scrapedConsoleGames = consoleGames
                print ('%s console games successfully scraped\n' % (console))
                break # success
            except Exception as exc:
                print ('%s console generated an exception on attempt %d: %s' % (console, attempt + 1, exc))
                if attempt < max_retries - 1:
                    pause = random.uniform(5, 10)
                    print("Waiting %.2f seconds before retrying..." % pause)
                    time.sleep(pause)
        
        allGames = allGames + scrapedConsoleGames
        
        if i < len(CONSOLES) - 1:
            pause = random.uniform(10, 20)
            print("Waiting %.2f seconds before scraping next console to avoid bot detection...\n" % pause)
            time.sleep(pause)

    gameCsv(allGames)


if __name__== "__main__":
    """Entry point for our program
    """
    print ('Scraping values from pricecharting.com\n')
    main()
    print ('Finished scraping values from pricecharting.com')