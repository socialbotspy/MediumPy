""" Common utilities """
# import time
# import datetime
from math import ceil
# from math import radians
# from math import degrees as rad2deg
# from math import cos
# import random
import re
# import regex
import signal
# import os
# import sys
# from sys import exit as clean_exit
# from platform import system
from platform import python_version
# from subprocess import call
# import csv
import sqlite3
# import json
from contextlib import contextmanager
# from tempfile import gettempdir
# import emoji
# from emoji.unicode_codes import UNICODE_EMOJI
from argparse import ArgumentParser

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By

from socialcommons.time_util import sleep
from socialcommons.time_util import sleep_actual
from .database_engine import get_database
from socialcommons.quota_supervisor import quota_supervisor
from .settings import Settings
# from .settings import Selectors

from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import TimeoutException

def getUserData(Settings, query,
                browser,
                basequery="return window._sharedData.entry_data.ProfilePage["
                          "0]."):
    try:
        data = browser.execute_script(
            basequery + query)
        return data
    except WebDriverException:
        browser.execute_script("location.reload()")
        update_activity(Settings)

        data = browser.execute_script(
            basequery + query)
        return data


def update_activity(Settings, action="server_calls"):
    """ Record every Instagram server call (page load, content load, likes,
        comments, connects, unconnect). """
    # check action availability
    quota_supervisor(Settings, "server_calls")

    # get a DB and start a connection
    db, id = get_database(Settings)
    conn = sqlite3.connect(db)

    with conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # collect today data
        cur.execute("SELECT * FROM recordActivity WHERE profile_id=:var AND "
                    "STRFTIME('%Y-%m-%d %H', created) == STRFTIME('%Y-%m-%d "
                    "%H', 'now', 'localtime')",
                    {"var": id})
        data = cur.fetchone()

        if data is None:
            # create a new record for the new day
            cur.execute("INSERT INTO recordActivity VALUES "
                        "(?, 0, 0, 0, 0, 1, STRFTIME('%Y-%m-%d %H:%M:%S', "
                        "'now', 'localtime'))",
                        (id,))

        else:
            # sqlite3.Row' object does not support item assignment -> so,
            # convert it into a new dict
            data = dict(data)

            # update
            data[action] += 1
            quota_supervisor(Settings, action, update=True)

            if action != "server_calls":
                # always update server calls
                data["server_calls"] += 1
                quota_supervisor(Settings, "server_calls", update=True)

            sql = ("UPDATE recordActivity set "
                   "likes = ?, comments = ?, follows = ?, unfollows = ?, server_calls = ?, "
                   "created = STRFTIME('%Y-%m-%d %H:%M:%S', 'now', "
                   "'localtime') "
                   "WHERE  profile_id=? AND STRFTIME('%Y-%m-%d %H', created) "
                   "== "
                   "STRFTIME('%Y-%m-%d %H', 'now', 'localtime')")

            cur.execute(sql, (data['likes'], data['comments'], data['follows'], data['unfollows'], data['server_calls'], id))

        # commit the latest changes
        conn.commit()

def click_element(browser, element, tryNum=0):
    """
    There are three (maybe more) different ways to "click" an element/button.
    1. element.click()
    2. element.send_keys("\n")
    3. browser.execute_script("document.getElementsByClassName('" +
    element.get_attribute("class") + "')[0].click()")

    I'm guessing all three have their advantages/disadvantages
    Before committing over this code, you MUST justify your change
    and potentially adding an 'if' statement that applies to your
    specific case. See the connecting issue for more details
    https://medium.com/timgrossmann/MediumPy/issues/1232

    explaination of the connecting recursive function:
      we will attempt to click the element given, if an error is thrown
      we know something is wrong (element not in view, element doesn't
      exist, ...). on each attempt try and move the screen around in
      various ways. if all else fails, programmically click the button
      using `execute_script` in the browser.
      """

    try:
        # use Selenium's built in click function
        element.click()

        # update server calls after a successful click by selenium
        update_activity()

    except Exception:
        # click attempt failed
        # try something funky and try again

        if tryNum == 0:
            # try scrolling the element into view
            browser.execute_script(
                "document.getElementsByClassName('" + element.get_attribute(
                    "class") + "')[0].scrollIntoView({ inline: 'center' });")

        elif tryNum == 1:
            # well, that didn't work, try scrolling to the top and then
            # clicking again
            browser.execute_script("window.scrollTo(0,0);")

        elif tryNum == 2:
            # that didn't work either, try scrolling to the bottom and then
            # clicking again
            browser.execute_script(
                "window.scrollTo(0,document.body.scrollHeight);")

        else:
            # try `execute_script` as a last resort
            # print("attempting last ditch effort for click, `execute_script`")
            browser.execute_script(
                "document.getElementsByClassName('" + element.get_attribute(
                    "class") + "')[0].click()")
            # update server calls after last click attempt by JS
            update_activity()
            # end condition for the recursive function
            return

        # update server calls after the scroll(s) in 0, 1 and 2 attempts
        update_activity()

        # sleep for 1 second to allow window to adjust (may or may not be
        # needed)
        sleep_actual(1)

        tryNum += 1

        # try again!
        click_element(browser, element, tryNum)


def format_number(number):
    """
    Format number. Remove the unused comma. Replace the concatenation with
    relevant zeros. Remove the dot.

    :param number: str

    :return: int
    """
    formatted_num = number.replace(',', '')
    formatted_num = re.sub(r'(k)$', '00' if '.' in formatted_num else '000',
                           formatted_num)
    formatted_num = re.sub(r'(m)$',
                           '00000' if '.' in formatted_num else '000000',
                           formatted_num)
    formatted_num = formatted_num.replace('.', '')
    return int(formatted_num)

def get_relationship_counts(browser, userid, logger):
    try:
        web_address_navigator(Settings, browser, "https://medium.com/profile/" + userid)
        leftsidelinks = browser.find_elements_by_css_selector("li > a")
        for link in leftsidelinks:
            href = link.get_attribute('href')
            page = href.split('/')[-1]
            if page=='followers':                
                followers = link.text.replace('Followers', '')
            elif page=='following':
                following = link.text.replace('Following', '')
            else:
                pass
    except Exception as e:
        print('get_relationship_counts', e)
    return format_number(followers), format_number(following)

def web_address_navigator(Settings, browser, link):
    """Checks and compares current URL of web page and the URL to be
    navigated and if it is different, it does navigate"""
    current_url = get_current_url(browser)
    total_timeouts = 0
    page_type = None  # file or directory

    # remove slashes at the end to compare efficiently
    if current_url is not None and current_url.endswith('/'):
        current_url = current_url[:-1]

    if link.endswith('/'):
        link = link[:-1]
        page_type = "dir"  # slash at the end is a directory

    new_navigation = (current_url != link)

    if current_url is None or new_navigation:
        link = link + '/' if page_type == "dir" else link  # directory links
        # navigate faster

        while True:
            try:
                browser.get(link)
                # update server calls
                update_activity(Settings)
                sleep(2)
                break

            except TimeoutException as exc:
                if total_timeouts >= 7:
                    raise TimeoutException(
                        "Retried {} times to GET '{}' webpage "
                        "but failed out of a timeout!\n\t{}".format(
                            total_timeouts,
                            str(link).encode("utf-8"),
                            str(exc).encode("utf-8")))
                total_timeouts += 1
                sleep(2)


@contextmanager
def interruption_handler(threaded=False, SIG_type=signal.SIGINT,
                         handler=signal.SIG_IGN, notify=None, logger=None):
    """ Handles external interrupt, usually initiated by the user like
    KeyboardInterrupt with CTRL+C """
    if notify is not None and logger is not None:
        logger.warning(notify)

    if not threaded:
        original_handler = signal.signal(SIG_type, handler)

    try:
        yield

    finally:
        if not threaded:
            signal.signal(SIG_type, original_handler)


def highlight_print(Settings, username=None, message=None, priority=None, level=None,
                    logger=None):
    """ Print headers in a highlighted style """
    # can add other highlighters at other priorities enriching this function

    # find the number of chars needed off the length of the logger message
    output_len = (28 + len(username) + 3 + len(message) if logger
                  else len(message))
    show_logs = Settings.show_logs

    if priority in ["initialization", "end"]:
        # OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO
        # E.g.:          Session started!
        # oooooooooooooooooooooooooooooooooooooooooooooooo
        upper_char = "O"
        lower_char = "o"

    elif priority == "login":
        # ................................................
        # E.g.:        Logged in successfully!
        # ''''''''''''''''''''''''''''''''''''''''''''''''
        upper_char = "."
        lower_char = "'"

    elif priority == "feature":  # feature highlighter
        # ________________________________________________
        # E.g.:    Starting to interact by users..
        # """"""""""""""""""""""""""""""""""""""""""""""""
        upper_char = "_"
        lower_char = "\""

    elif priority == "user iteration":
        # ::::::::::::::::::::::::::::::::::::::::::::::::
        # E.g.:            User: [1/4]
        upper_char = ":"
        lower_char = None

    elif priority == "post iteration":
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # E.g.:            Post: [2/10]
        upper_char = "~"
        lower_char = None

    elif priority == "workspace":
        # ._. ._. ._. ._. ._. ._. ._. ._. ._. ._. ._. ._.
        # E.g.: |> Workspace in use: "C:/Users/El/MediumPy"
        upper_char = " ._. "
        lower_char = None

    if (upper_char
            and (show_logs
                 or priority == "workspace")):
        print("\n{}".format(
            upper_char * int(ceil(output_len / len(upper_char)))))

    if level == "info":
        if logger:
            logger.info(message)
        else:
            print(message)

    elif level == "warning":
        if logger:
            logger.warning(message)
        else:
            print(message)

    elif level == "critical":
        if logger:
            logger.critical(message)
        else:
            print(message)

    if (lower_char
            and (show_logs
                 or priority == "workspace")):
        print("{}".format(
            lower_char * int(ceil(output_len / len(lower_char)))))

def explicit_wait(browser, track, ec_params, logger, timeout=35, notify=True):
    """
    Explicitly wait until expected condition validates

    :param browser: webdriver instance
    :param track: short name of the expected condition
    :param ec_params: expected condition specific parameters - [param1, param2]
    :param logger: the logger instance
    """
    # list of available tracks:
    # <https://seleniumhq.medium.io/selenium/docs/api/py/webdriver_support/
    # selenium.webdriver.support.expected_conditions.html>

    if not isinstance(ec_params, list):
        ec_params = [ec_params]

    # find condition according to the tracks
    if track == "VOEL":
        elem_address, find_method = ec_params
        ec_name = "visibility of element located"

        find_by = (By.XPATH if find_method == "XPath" else
                   By.CSS_SELECTOR if find_method == "CSS" else
                   By.CLASS_NAME)
        locator = (find_by, elem_address)
        condition = ec.visibility_of_element_located(locator)

    elif track == "TC":
        expect_in_title = ec_params[0]
        ec_name = "title contains '{}' string".format(expect_in_title)

        condition = ec.title_contains(expect_in_title)

    elif track == "PFL":
        ec_name = "page fully loaded"
        condition = (lambda browser: browser.execute_script(
            "return document.readyState")
                                     in ["complete" or "loaded"])

    elif track == "SO":
        ec_name = "staleness of"
        element = ec_params[0]

        condition = ec.staleness_of(element)

    # generic wait block
    try:
        wait = WebDriverWait(browser, timeout)
        result = wait.until(condition)

    except TimeoutException:
        if notify is True:
            logger.info(
                "Timed out with failure while explicitly waiting until {}!\n"
                    .format(ec_name))
        return False

    return result


def get_current_url(browser):
    """ Get URL of the loaded webpage """
    try:
        current_url = browser.execute_script("return window.location.href")

    except WebDriverException:
        try:
            current_url = browser.current_url

        except WebDriverException:
            current_url = None

    return current_url

def truncate_float(number, precision, round=False):
    """ Truncate (shorten) a floating point value at given precision """

    # don't allow a negative precision [by mistake?]
    precision = abs(precision)

    if round:
        # python 2.7+ supported method [recommended]
        short_float = round(number, precision)

        # python 2.6+ supported method
        """short_float = float("{0:.{1}f}".format(number, precision))
        """

    else:
        operate_on = 1  # returns the absolute number (e.g. 11.0 from 11.456)

        for i in range(precision):
            operate_on *= 10

        short_float = float(int(number * operate_on)) / operate_on

    return short_float

def save_account_progress(Settings, browser, username, userid, logger):
    """
    Check account current progress and update database

    Args:
        :browser: web driver
        :username: Account to be updated
        :logger: library to log actions
    """
    logger.info('Saving account progress...')
    followers, following = get_relationship_counts(browser, userid, logger)

    # save profile total posts
    posts = getUserData(Settings, "graphql.user.edge_owner_to_timeline_media.count",
                        browser)

    try:
        # DB instance
        db, id = get_database(Settings)
        conn = sqlite3.connect(db)
        with conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            sql = ("INSERT INTO accountsProgress (profile_id, followers, "
                   "following, total_posts, created, modified) "
                   "VALUES (?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S'), "
                   "strftime('%Y-%m-%d %H:%M:%S'))")
            cur.execute(sql, (id, followers, following, posts))
            conn.commit()
    except Exception:
        logger.exception('message')

def parse_cli_args():
    """ Parse arguments passed by command line interface """

    AP_kwargs = dict(prog="MediumPy",
                     description="Parse MediumPy constructor's arguments",
                     epilog="And that's how you'd pass arguments by CLI..",
                     conflict_handler="resolve")
    if python_version() < "3.5":
        parser = CustomizedArgumentParser(**AP_kwargs)
    else:
        AP_kwargs.update(allow_abbrev=False)
        parser = ArgumentParser(**AP_kwargs)

    """ Flags that REQUIRE a value once added
    ```python quickstart.py --username abc```
    """
    parser.add_argument(
        "-u", "--username", help="Username must be emailid", type=str, metavar="abc@gmail.com")
    parser.add_argument(
        "-p", "--password", help="Password", type=str, metavar="123")
    parser.add_argument(
        "-ui", "--userid", help="userid is the partstring on URL of your home page", type=str, metavar="Abc-Def")
    parser.add_argument(
        "-pd", "--page-delay", help="Implicit wait", type=int, metavar=25)
    parser.add_argument(
        "-pa", "--proxy-address", help="Proxy address",
        type=str, metavar="192.168.1.1")
    parser.add_argument(
        "-pp", "--proxy-port", help="Proxy port", type=int, metavar=8080)

    """ Auto-booleans: adding these flags ENABLE themselves automatically
    ```python quickstart.py --use-firefox```
    """
    parser.add_argument(
        "-uf", "--use-firefox", help="Use Firefox",
        action="store_true", default=None)
    parser.add_argument(
        "-hb", "--headless-browser", help="Headless browser",
        action="store_true", default=None)
    parser.add_argument(
        "-dil", "--disable-image-load", help="Disable image load",
        action="store_true", default=None)
    parser.add_argument(
        "-bsa", "--bypass-suspicious-attempt",
        help="Bypass suspicious attempt", action="store_true", default=None)
    parser.add_argument(
        "-bwm", "--bypass-with-mobile", help="Bypass with mobile phone",
        action="store_true", default=None)
    parser.add_argument(
        "-sdb", "--split-db", help="Split sqlite-db as mediumpy_{username}.db",
        action="store_true", default=None)

    """ Style below can convert strings into booleans:
    ```parser.add_argument("--is-debug",
                           default=False,
                           type=lambda x: (str(x).capitalize() == "True"))```

    So that, you can pass bool values explicitly from CLI,
    ```python quickstart.py --is-debug True```

    NOTE: This style is the easiest of it and currently not being used.
    """

    args, args_unknown = parser.parse_known_args()
    """ Once added custom arguments if you use a reserved name of core flags
    and don't parse it, e.g.,
    `-ufa` will misbehave cos it has `-uf` reserved flag in it.

    But if you parse it, it's okay.
    """

    return args

class CustomizedArgumentParser(ArgumentParser):
    """
     Subclass ArgumentParser in order to turn off
    the abbreviation matching on older pythons.

    `allow_abbrev` parameter was added by Python 3.5 to do it.
    Thanks to @paul.j3 - https://bugs.python.org/msg204678 for this solution.
    """

