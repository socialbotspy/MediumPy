"""Module only used for the login part of the script"""
# import built-in & third-party modules
import time
import pickle
from selenium.webdriver.common.action_chains import ActionChains

# import MediumPy modules
from socialcommons.time_util import sleep
from socialcommons.util import update_activity
from socialcommons.util import web_address_navigator
from socialcommons.util import reload_webpage
# from socialcommons.util import click_element
from socialcommons.util import explicit_wait
from .settings import Settings

# import exceptions
# from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import WebDriverException

def check_authorization(browser, Settings, base_url, username, userid, method, logger, logfolder, notify=True):
    """ Check if user is NOW logged in """
    if notify is True:
        logger.info("Checking if '{}' is logged in...".format(username))
    prof_img = browser.find_elements_by_css_selector("span.IdentityPhoto")
    if len(prof_img) >= 1:
        # create cookie for username
        pickle.dump(browser.get_cookies(), open(
            '{0}{1}_cookie.pkl'.format(logfolder, username), 'wb'))
        return True
    return False

def login_user(browser,
               username,
               password,
               userid,
               logger,
               logfolder):
    """Logins the user with the given username and password"""
    assert username, 'Username not provided'
    assert password, 'Password not provided'

    print(username, password)
    homepage = "https://www.medium.com/"
    web_address_navigator(browser, homepage, Settings)
    cookie_loaded = False

    # try to load cookie from username
    try:
        for cookie in pickle.load(open('{0}{1}_cookie.pkl'
                                       .format(logfolder, username), 'rb')):
            browser.add_cookie(cookie)
            cookie_loaded = True
    except (WebDriverException, OSError, IOError):
        print("Cookie file not found, creating cookie...")

    # include time.sleep(1) to prevent getting stuck on google.com
    time.sleep(1)

    web_address_navigator(browser, homepage, Settings)
    reload_webpage(browser, Settings)

    # if user is still not logged in, then there is an issue with the cookie
    # so go create a new cookie..

    # cookie has been LOADED, so the user SHOULD be logged in
    # check if the user IS logged in
    if cookie_loaded:
        login_state = check_authorization(browser, Settings,
                                        "https://www.medium.com",
                                        username,
                                        userid,
                                        "activity counts",
                                        logger,
                                        logfolder,
                                        True)
        print('check_authorization:', login_state)
        if login_state is True:
            # dismiss_notification_offer(browser, logger)
            return True
        else:
            print("Issue with cookie for user {}. Creating "
                  "new cookie...".format(username))

    input_username_XP = '//div[2]/div[1]/input[@name="email"]'    
    input_usernames = browser.find_elements_by_xpath(input_username_XP)#TODO : Two tags found just take the last one

    print('moving to input_username')
    print('entering input_username: {}'.format(username))
    #email login doesn't reprompt
    (ActionChains(browser)
     .move_to_element(input_usernames[-1])
     .click()
     .send_keys(username)
     .perform())

    # update server calls for both 'click' and 'send_keys' actions
    for i in range(2):
        update_activity(Settings)

    sleep(1)

    #  password
    input_passeord_XP = '//div[2]/div[2]/input[@name="password"]'
    input_passwords = browser.find_elements_by_xpath(input_passeord_XP)

    print('entering input_password')
    (ActionChains(browser)
     .move_to_element(input_passwords[-1])
     .click()
     .send_keys(password)
     .perform())

    # update server calls for both 'click' and 'send_keys' actions
    for i in range(2):
        update_activity(Settings)

    sleep(1)

    print('submitting login_button')
    login_button_XP = '//div[2]/div[3]/input'
    login_button = browser.find_element_by_xpath(login_button_XP)

    (ActionChains(browser)
     .move_to_element(login_button)
     .click()
     .perform())

    # update server calls
    update_activity(Settings)

    sleep(2)

    # wait until page fully load
    explicit_wait(browser, "PFL", [], logger, 5)

    # Check if user is logged-in (If there's two 'nav' elements)
    login_state = check_authorization(browser, Settings,
                                    "https://www.medium.com/login",
                                    username,
                                    userid,
                                    "activity counts",
                                    logger,
                                    logfolder,
                                    True)
    print('check_authorization again:', login_state)
    return login_state



