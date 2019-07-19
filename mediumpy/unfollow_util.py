from datetime import datetime
import sqlite3

from socialcommons.time_util import sleep
from .database_engine import get_database
from socialcommons.quota_supervisor import quota_supervisor
from socialcommons.print_log_writer import log_followed_pool

from socialcommons.util import web_address_navigator
from socialcommons.util import update_activity
from socialcommons.util import explicit_wait
from socialcommons.util import find_user_id
from socialcommons.util import get_action_delay
from socialcommons.util import emergency_exit
from socialcommons.util import click_visibly
from socialcommons.util import click_element
from socialcommons.util import reload_webpage

from .xpath import read_xpath

from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotVisibleException
from .settings import Settings

def follow_restriction(operation, username, limit, logger):
    """ Keep track of the followed users and help avoid excessive follow of
    the same user """

    try:
        # get a DB and start a connection
        db, id = get_database(Settings)
        conn = sqlite3.connect(db)

        with conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute(
                "SELECT * FROM followRestriction WHERE profile_id=:id_var "
                "AND username=:name_var",
                {"id_var": id, "name_var": username})
            data = cur.fetchone()
            follow_data = dict(data) if data else None

            if operation == "write":
                if follow_data is None:
                    # write a new record
                    cur.execute(
                        "INSERT INTO followRestriction (profile_id, "
                        "username, times) VALUES (?, ?, ?)",
                        (id, username, 1))
                else:
                    # update the existing record
                    follow_data["times"] += 1
                    sql = "UPDATE followRestriction set times = ? WHERE " \
                          "profile_id=? AND username = ?"
                    cur.execute(sql, (follow_data["times"], id, username))

                # commit the latest changes
                conn.commit()

            elif operation == "read":
                if follow_data is None:
                    return False

                elif follow_data["times"] < limit:
                    return False

                else:
                    exceed_msg = "" if follow_data[
                        "times"] == limit else "more than "
                    logger.info("---> {} has already been followed {}{} times"
                                .format(username, exceed_msg, str(limit)))
                    return True

    except Exception as exc:
        logger.error(
            "Dap! Error occurred with follow Restriction:\n\t{}".format(
                str(exc).encode("utf-8")))

    finally:
        if conn:
            # close the open connection
            conn.close()

def follow_user(browser, track, login, userid_to_follow, button, blacklist,
                logger, logfolder, Settings):
    """ Follow a user either from the profile page or post page or dialog
    box """
    # list of available tracks to follow in: ["profile", "post" "dialog"]

    # check action availability
    if quota_supervisor(Settings, "follows") == "jump":
        return False, "jumped"

    if track in ["profile", "post"]:
        if track == "profile":
            # check URL of the webpage, if it already is user's profile
            # page, then do not navigate to it again
            user_link = "https://www.medium.com/{}/".format(userid_to_follow)
            web_address_navigator( browser, user_link, Settings)

        # find out CURRENT following status
        following_status, follow_button = \
            get_following_status(browser,
                                 track,
                                 login,
                                 userid_to_follow,
                                 None,
                                 logger,
                                 logfolder)
        if following_status in ["Follow", "Follow Back"]:
            click_visibly(browser, Settings, follow_button)  # click to follow
            follow_state, msg = verify_action(browser, "follow", track, login,
                                              userid_to_follow, None, logger,
                                              logfolder)
            if follow_state is not True:
                return False, msg

        elif following_status in ["Following", "Requested"]:
            if following_status == "Following":
                logger.info(
                    "--> Already following '{}'!\n".format(userid_to_follow))

            elif following_status == "Requested":
                logger.info("--> Already requested '{}' to follow!\n".format(
                    userid_to_follow))

            sleep(1)
            return False, "already followed"

        elif following_status in ["Unblock", "UNAVAILABLE"]:
            if following_status == "Unblock":
                failure_msg = "user is in block"

            elif following_status == "UNAVAILABLE":
                failure_msg = "user is inaccessible"

            logger.warning(
                "--> Couldn't follow '{}'!\t~{}".format(userid_to_follow,
                                                        failure_msg))
            return False, following_status

        elif following_status is None:
            # TODO:BUG:2nd login has to be fixed with userid of loggedin user
            sirens_wailing, emergency_state = emergency_exit(browser, Settings, "https://www.medium.com", login,
                                                             login, logger, logfolder)
            if sirens_wailing is True:
                return False, emergency_state

            else:
                logger.warning(
                    "--> Couldn't unfollow '{}'!\t~unexpected failure".format(
                        userid_to_follow))
                return False, "unexpected failure"
    elif track == "dialog":
        click_element(browser, Settings, button)
        sleep(3)

    # general tasks after a successful follow
    logger.info("--> Followed '{}'!".format(userid_to_follow.encode("utf-8")))
    update_activity(Settings, 'follows')

    # get user ID to record alongside username
    user_id = get_user_id(browser, track, userid_to_follow, logger)

    logtime = datetime.now().strftime('%Y-%m-%d %H:%M')
    log_followed_pool(login, userid_to_follow, logger,
                      logfolder, logtime, user_id)

    follow_restriction("write", userid_to_follow, None, logger)

    # if blacklist['enabled'] is True:
    #     action = 'followed'
    #     add_user_to_blacklist(userid_to_follow,
    #                           blacklist['campaign'],
    #                           action,
    #                           logger,
    #                           logfolder)

    # get the post-follow delay time to sleep
    naply = get_action_delay("follow", Settings)
    sleep(naply)

    return True, "success"

def get_user_id(browser, track, username, logger):
    """ Get user's ID either from a profile page or post page """
    user_id = "unknown"

    if track != "dialog":  # currently do not get the user ID for follows
        # from 'dialog'
        user_id = find_user_id(Settings, browser, track, username, logger)

    return user_id

def get_following_status(browser, track, username, person, person_id, logger,
                         logfolder):
    """ Verify if you are following the user in the loaded page """
    if track == "profile":
        ig_homepage = "https://www.medium.com/"
        web_address_navigator( browser, ig_homepage + person, Settings)

    follow_button_XP = ('//*[@id="page-container"]/div/div/ul/li/div/div/span/button[@type="button"]/span[text()="Follow"]')
    failure_msg = "--> Unable to detect the following status of '{}'!"
    # user_inaccessible_msg = (
    #     "Couldn't access the profile page of '{}'!\t~might have changed the"
    #     " username".format(person))

    # check if the page is available
    # valid_page = is_page_available(browser, logger, Settings)
    # if not valid_page:
    #     logger.warning(user_inaccessible_msg)
    #     person_new = verify_username_by_id(browser,
    #                                        username,
    #                                        person,
    #                                        None,
    #                                        logger,
    #                                        logfolder)
    #     if person_new:
    #         web_address_navigator( browser, ig_homepage + person_new, Settings)
    #         valid_page = is_page_available(browser, logger, Settings)
    #         if not valid_page:
    #             logger.error(failure_msg.format(person_new.encode("utf-8")))
    #             return "UNAVAILABLE", None
    #     else:
    #         logger.error(failure_msg.format(person.encode("utf-8")))
    #         return "UNAVAILABLE", None

    # wait until the follow button is located and visible, then get it
    follow_button = explicit_wait(browser, "VOEL", [follow_button_XP, "XPath"], logger, 7, False)
    logger.info("follow_button =  {}".format(follow_button))

    if not follow_button:
        browser.execute_script("location.reload()")
        update_activity(Settings)

        follow_button = explicit_wait(browser, "VOEL",
                                      [follow_button_XP, "XPath"], logger, 14,
                                      False)
        logger.info("follow_button retried =  {}".format(follow_button))

        if not follow_button:
            # cannot find the any of the expected buttons
            logger.error(failure_msg.format(person.encode("utf-8")))
            return None, None

    # get follow status
    following_status = follow_button.text
    logger.info("following_status returned =  {}".format(following_status))

    return following_status, follow_button


def verify_action(browser, action, track, username, person, person_id, logger,
                  logfolder):
    """ Verify if the action has succeeded """
    # currently supported actions are follow & unfollow

    retry_count = 0

    if action in ["follow", "unfollow"]:

        # assuming button_change testing is relevant to those actions only
        button_change = False

        if action == "follow":
            post_action_text_correct = ["Following", "Requested"]
            post_action_text_fail = ["Follow", "Follow Back", "Unblock"]

        elif action == "unfollow":
            post_action_text_correct = ["Follow", "Follow Back", "Unblock"]
            post_action_text_fail = ["Following", "Requested"]

        while True:

            # count retries at beginning
            retry_count += 1

            # find out CURRENT follow status (this is safe as the follow button is before others)
            following_status, follow_button = get_following_status(browser,
                                                                   track,
                                                                   username,
                                                                   person,
                                                                   person_id,
                                                                   logger,
                                                                   logfolder)
            if following_status in post_action_text_correct:
                button_change = True
            elif following_status in post_action_text_fail:
                button_change = False
            else:
                logger.error(
                    "Hey! Last {} is not verified out of an unexpected "
                    "failure!".format(action))
                return False, "unexpected"


            if button_change:
                break
            else:
                if retry_count == 1:
                    reload_webpage(browser)

                elif retry_count == 2:
                    # handle it!
                    # try to do the action one more time!
                    click_visibly(browser, follow_button)

                    if action == "unfollow":
                        confirm_unfollow(browser)

                    sleep(4)

                elif retry_count == 3:
                    logger.warning("Phew! Last {0} is not verified."
                                   "\t~'{1}' might be temporarily blocked "
                                   "from {0}ing\n"
                                   .format(action, username))
                    sleep(210)
                    return False, "temporary block"

        if retry_count == 2:
            logger.info(
                "Last {} is verified after reloading the page!".format(
                    action))

    return True, "success"



def confirm_unfollow(browser):
    """ Deal with the confirmation dialog boxes during an unfollow """
    attempt = 0

    while attempt < 3:
        try:
            attempt += 1
            button_xp = read_xpath(confirm_unfollow.__name__,"button_xp")  # "//button[contains(
            # text(), 'Unfollow')]"
            unfollow_button = browser.find_element_by_xpath(button_xp)

            if unfollow_button.is_displayed():
                click_element(browser, unfollow_button)
                sleep(2)
                break

        except (ElementNotVisibleException, NoSuchElementException) as exc:
            # prob confirm dialog didn't pop up
            if isinstance(exc, ElementNotVisibleException):
                break

            elif isinstance(exc, NoSuchElementException):
                sleep(1)
