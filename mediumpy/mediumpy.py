import time
import logging
import os
import random
from sys import exit as clean_exit
from math import ceil

from .login_util import login_user
from .settings import Settings

from .unfollow_util  import follow_restriction
from .unfollow_util  import follow_user

from contextlib import contextmanager
from tempfile import gettempdir

from socialcommons.print_log_writer import log_following_num

from .util import parse_cli_args
from .util import interruption_handler
from .util import highlight_print
from .util import truncate_float
from .util import format_number
from .util import web_address_navigator
from .util import save_account_progress
from .util import get_relationship_counts

from socialcommons.time_util import sleep

from socialcommons.browser import close_browser
# from socialcommons.file_manager import get_workspace
from socialcommons.file_manager import get_logfolder
from socialcommons.browser import set_selenium_local_session

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

ROW_HEIGHT = 141

class MediumPy:
    """Class to be instantiated to use the script"""
    def __init__(self,
                 username=None,
                 password=None,
                 userid=None,
                 selenium_local_session=True,
                 browser_profile_path=None,
                 page_delay=25,
                 show_logs=True,
                 headless_browser=False,
                 disable_image_load=False,
                 multi_logs=True,
                 use_firefox=False):

        cli_args = parse_cli_args()
        username = cli_args.username or username
        password = cli_args.password or password
        userid = cli_args.userid or userid
        page_delay = cli_args.page_delay or page_delay
        headless_browser = cli_args.headless_browser or headless_browser
        disable_image_load = cli_args.disable_image_load or disable_image_load

        self.browser = None
        self.headless_browser = headless_browser
        self.use_firefox = use_firefox
        self.selenium_local_session = selenium_local_session
        self.disable_image_load = disable_image_load

        self.username = username or os.environ.get('TWITTER_USER')
        self.password = password or os.environ.get('TWITTER_PW')
        self.email = username or os.environ.get('TWITTER_EMAIL')
        self.userid = userid

        Settings.profile["name"] = self.username
        self.browser_profile_path = browser_profile_path

        self.page_delay = page_delay
        self.followed = 0
        self.followed_by = 0
        self.following_num = 0

        self.follow_times = 1
        self.do_follow = False

        self.dont_include = set()
        self.white_list = set()

        self.user_interact_amount = 0
        self.user_interact_media = None
        self.user_interact_percentage = 0
        self.user_interact_random = False

        self.jumps = {
            "consequent": {"likes": 0, "comments": 0, "follows": 0, "unfollows": 0},
            "limit": {"likes": 7, "comments": 3, "follows": 5, "unfollows": 4}
        }

        self.start_time = time.time()
        # assign logger
        self.show_logs = show_logs
        Settings.show_logs = show_logs or None
        self.multi_logs = multi_logs
        self.logfolder = get_logfolder(self.username, self.multi_logs, Settings)
        self.logger = self.get_mediumpy_logger(self.show_logs)

        if self.selenium_local_session is True:
            self.set_selenium_local_session(Settings)

    def get_mediumpy_logger(self, show_logs):
        """
        Handles the creation and retrieval of loggers to avoid
        re-instantiation.
        """

        existing_logger = Settings.loggers.get(self.username)
        if existing_logger is not None:
            return existing_logger
        else:
            # initialize and setup logging system for the MediumPy object
            logger = logging.getLogger(self.username)
            logger.setLevel(logging.DEBUG)
            file_handler = logging.FileHandler(
                '{}general.log'.format(self.logfolder))
            file_handler.setLevel(logging.DEBUG)
            extra = {"username": self.username}
            logger_formatter = logging.Formatter(
                '%(levelname)s [%(asctime)s] [%(username)s]  %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S')
            file_handler.setFormatter(logger_formatter)
            logger.addHandler(file_handler)

            if show_logs is True:
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.DEBUG)
                console_handler.setFormatter(logger_formatter)
                logger.addHandler(console_handler)

            logger = logging.LoggerAdapter(logger, extra)

            Settings.loggers[self.username] = logger
            Settings.logger = logger
            return logger

    def set_selenium_local_session(self, Settings):
        self.browser, err_msg = \
            set_selenium_local_session(None,
                                       None,
                                       None,
                                       self.headless_browser,
                                       self.use_firefox,
                                       self.browser_profile_path,
                                       # Replaces
                                       # browser User
                                       # Agent from
                                       # "HeadlessChrome".
                                       self.disable_image_load,
                                       self.page_delay,
                                       self.logger,
                                       Settings)
        if len(err_msg) > 0:
            raise SocialPyError(err_msg)


    def SignInToGoogle(self):
        """
        Sign into Medium using a Google account.
        browser: selenium driver used to interact with the page.
        return: true if successfully logged in : false if login failed.
        """
        signInCompleted = False

        try:
            self.browser.find_element_by_xpath('//button[contains(text(),"Sign in or sign up with email")]').click()
            self.browser.find_element_by_name('email').send_keys(this.username)
            self.browser.find_element_by_class_name('button--google').click()
            self.browser.find_element_by_id("next").click()
            time.sleep(3)
            self.browser.find_element_by_id('Passwd').send_keys(this.password)
            self.browser.find_element_by_id('signIn').click()
            time.sleep(3)
            signInCompleted = True
        except:
            pass

        if not signInCompleted:
            try:
                self.browser.find_element_by_id("identifierNext").click()
                time.sleep(3)
                self.browser.find_element_by_name('password').send_keys(this.password)
                self.browser.find_element_by_id('passwordNext').click()
                time.sleep(3)
                signInCompleted = True
            except:
                print("Problem logging into Medium with Google.")
                pass

        return signInCompleted

    def login(self):
        # if os.path.isfile(SESSION_FILE):
        #     print("Found session file %s" % SESSION_FILE)
        #     browser.get("https://medium.com")
        #     with open(SESSION_FILE, 'rb') as i:
        #         cookies = pickle.load(i)
        #         for cookie in cookies:
        #             browser.add_cookie(cookie)
        #     return True

        # serviceToSignWith = LOGIN_SERVICE.lower()
        signInCompleted = False
        print('Signing in...')

        self.browser.get('https://medium.com/m/signin?redirect=https%3A%2F%2Fmedium.com%2F')

        try:
            signin_btn = self.browser.find_element_by_xpath('//button[contains(text(),"Sign in")]').click()
            signin_btn.click()
        except:
            pass

        if not self.SignInToGoogle():
            message = "Wrong login data!"
            highlight_print(Settings, self.username,
                            message,
                            "login",
                            "critical",
                            self.logger)
        else:
            message = "Logged in successfully!"
            highlight_print(Settings, self.username,
                            message,
                            "login",
                            "info",
                            self.logger)
            # try to save account progress
            try:
                save_account_progress(Settings,
                                    self.browser,
                                    self.username,
                                    self.userid,
                                    self.logger)
            except Exception:
                self.logger.warning(
                    'Unable to save account progress, skipping data update')

        """Used to login the user either with the username and password"""
        # if not login_user(self.browser,
        #                   self.username,
        #                   self.password,
        #                   self.userid,
        #                   self.logger,
        #                   self.logfolder):
        # else:
        #     # try to save account progress
        #     try:
        #         save_account_progress(Settings,
        #                             self.browser,
        #                             self.username,
        #                             self.userid,
        #                             self.logger)
        #     except Exception:
        #         self.logger.warning(
        #             'Unable to save account progress, skipping data update')

        # self.followed_by, self.following_num = self.get_relationship_counts()

        return self

    def set_do_follow(self, enabled=False, percentage=0, times=1):
        self.follow_times = times
        self.do_follow = enabled
        return self

    def set_dont_include(self, friends=None):
        """Defines which accounts should not be unfollowed"""
        self.dont_include = set(friends) or set()
        self.white_list = set(friends) or set()
        return self

    def set_user_interact(self, amount=10, percentage=100, randomize=False, media=None):
        """Define if posts of given user should be interacted"""
        self.user_interact_amount = amount
        self.user_interact_random = randomize
        self.user_interact_percentage = percentage
        self.user_interact_media = media
        return self

    def count_new_followers(self, sleep_delay=2):
        web_address_navigator(Settings, self.browser, "https://medium.com/notifications")
        self.logger.info('Browsing my notifications')
        delay_random = random.randint(
                    ceil(sleep_delay * 0.85),
                    ceil(sleep_delay * 1.14))
        sleep(delay_random)
        rows = self.browser.find_elements_by_css_selector("div > div > div > main > div > div > div > div > div > div > div > div > div > section > div > div > div > div > div > article > div > div")
        cnt = 0
        for row in rows:
            try:
                if "followed you" in row.text:
                    # self.logger.info(row.text)
                    if "others" in row.text:
                        splitted = row.text.split('others')[0].split(' ')
                        splitted = [x for x in splitted if x]
                        cnt = cnt + int(splitted[-1]) + 1
                    elif "others" in row.text:
                        cnt = cnt + 2
                    else:
                        cnt = cnt + 1
            except Exception as e:
                self.logger.error(e)
        return cnt

    def get_relationship_counts(self):
        return get_relationship_counts(self.browser, self.userid, self.logger)

    # def visit_and_unfollow(self, profilelink, sleep_delay=2):
    #     try:        
    #         self.logger.info('Visiting {}'.format(profilelink))
    #         web_address_navigator(Settings, self.browser, profilelink)
    #         delay_random = random.randint(
    #                     ceil(sleep_delay * 0.85),
    #                     ceil(sleep_delay * 1.14))
    #         button = self.browser.find_element_by_css_selector("div > span > a.ui_button.pressed")
    #         if button.text.split('\n')[0].strip()=='Follow':
    #             self.logger.info('Clicking {}'.format(button.text.split('\n')[0].strip()))
    #             button.click()
    #             sleep(delay_random)
    #             web_address_navigator(Settings, self.browser, profilelink)
    #             try:
    #                 button = self.browser.find_element_by_css_selector("div > span > a.ui_button.pressed")
    #                 return False
    #             except Exception as e:
    #                 self.logger.info('Button rightly flipped')
    #                 return True
    #         else:
    #             self.logger.info('Already {}'.format(button.text))
    #             return False
    #     except Exception as e:
    #         self.logger.error(e)
    #         return False
    #     return False

    # def visit_and_follow(self, profilelink, sleep_delay=2):
    #     try:        
    #         self.logger.info('Visiting {}'.format(profilelink))
    #         web_address_navigator(Settings, self.browser, profilelink)
    #         delay_random = random.randint(
    #                     ceil(sleep_delay * 0.85),
    #                     ceil(sleep_delay * 1.14))
    #         button = self.browser.find_element_by_css_selector("div.ui_button_inner > div.ui_button_label_count_wrapper > span.ui_button_label")
    #         if button.text.split('\n')[0].strip()=='Follow':
    #             self.logger.info('Clicking {}'.format(button.text.split('\n')[0].strip()))
    #             button.click()
    #             sleep(delay_random)
    #             web_address_navigator(Settings, self.browser, profilelink)
    #             try:
    #                 button = self.browser.find_element_by_css_selector("div.ui_button_inner > div.ui_button_label_count_wrapper > span.ui_button_label")
    #                 if button.text.split('\n')[0].strip()=='Following':
    #                     return True
    #                 else:
    #                     return False
    #             except Exception as e:
    #                 self.logger.info('Button rightly flipped')
    #                 return True
    #         else:
    #             self.logger.info('Already {}'.format(button.text))
    #             return False
    #     except Exception as e:
    #         self.logger.error(e)
    #         return False
    #     return False

    # def visit_and_upvote(self, post_link, sleep_delay=2):
    #     try:
    #         self.logger.info('Visiting {}'.format(post_link))
    #         web_address_navigator(Settings, self.browser, post_link)
    #         for i in range(3):
    #             self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    #         delay_random = random.randint(
    #                     ceil(sleep_delay * 0.85),
    #                     ceil(sleep_delay * 1.14))
    #         try:
    #             pressed_button = self.browser.find_element_by_css_selector("div.UpvotePrimaryItem > span > a.pressed")
    #             if pressed_button.text.split('\n')[0].strip()=='Upvote':
    #                 self.logger.info('Already {}'.format(pressed_button.text))
    #                 return False
    #         except Exception as e:
    #             unpressed_button = self.browser.find_element_by_css_selector("div.UpvotePrimaryItem > span > a")
    #             if unpressed_button.text.split('\n')[0].strip()=='Upvote':
    #                 self.logger.info('Clicking {}'.format(unpressed_button.text.split('\n')[0].strip()))
    #                 unpressed_button.click()
    #                 sleep(delay_random)
    #                 web_address_navigator(Settings, self.browser, post_link)
    #                 for i in range(3):
    #                     self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    #                 try:
    #                     pressed_button2 = self.browser.find_element_by_css_selector("div.UpvotePrimaryItem > span > a.pressed")
    #                     self.logger.info('Button rightly flipped')
    #                     return True
    #                 except Exception as e:
    #                     self.looger.error(e)
    #                     return False
    #             else:
    #                 self.logger.info('Already {}'.format(unpressed_button.text))
    #                 return False
    #     except Exception as e:
    #         self.logger.error(e)
    #         return False
    #     return False

    # def unfollow_users(self, skip=10, amount=100, sleep_delay=2):
    #     try:
    #         unfollowed = 0
    #         failed = 0
    #         web_address_navigator(Settings, self.browser, "https://medium.com/" + self.userid + "/following")
    #         rows = self.browser.find_elements_by_css_selector("div.IdentityPagedListItem")
    #         print('len(rows)', len(rows))
    #         profilelinks = []
    #         for i, row in enumerate(rows):
    #             try:
    #                 profilelink_tag = row.find_element_by_css_selector("div.ObjectCard-header > span > span > a.user")
    #                 profilelink = profilelink_tag.get_attribute("href")
    #                 self.logger.info(profilelink)
    #                 if i < skip:
    #                     self.logger.info("Skipping")
    #                 else:
    #                     profilelinks.append(profilelink)
    #             except Exception as e:
    #                 print(e)
    #         for profilelink in profilelinks:
    #             if self.visit_and_unfollow(profilelink):
    #                 unfollowed = unfollowed + 1
    #             self.logger.info('unfollowed in this iteration till now: {}'.format(unfollowed))
    #             if unfollowed > amount:
    #                 self.logger.info('Unfollowed too many times this hour. Returning')
    #                 return
    #     except Exception as e:
    #         print(e)

    # def follow_users_from_profile_links(self, prof_links, sleep_delay=2):
    #     delay_random = random.randint(
    #                 ceil(sleep_delay * 0.85),
    #                 ceil(sleep_delay * 1.14))
    #     followed = 0
    #     for prof_link in prof_links:
    #         if self.visit_and_follow(prof_link):
    #             followed += 1
    #         sleep(delay_random)
    #         self.logger.info('Followed till now: {}'.format(followed))
    #         if followed > 10:
    #             self.logger.info('Enough for now, lets return')
    #             return

    # def upvote_from_post_links(self, post_links, sleep_delay=2):
    #     delay_random = random.randint(
    #                 ceil(sleep_delay * 0.85),
    #                 ceil(sleep_delay * 1.14))
    #     upvoted = 0
    #     for post_link in post_links:
    #         if self.visit_and_upvote(post_link):
    #             upvoted += 1
    #         sleep(delay_random)
    #         self.logger.info('Upvoted till now: {}'.format(upvoted))
    #         if upvoted > 10:
    #             self.logger.info('Enough for now, lets return')
    #             return

    # def follow_all_here(self, amount, sleep_delay=2):
    #     followed = 0
    #     failed = 0
    #     delay_random = random.randint(
    #                 ceil(sleep_delay * 0.85),
    #                 ceil(sleep_delay * 1.14))
    #     rows = self.browser.find_elements_by_css_selector("div.IdentityPagedListItem")
    #     print('len(rows)', len(rows))
    #     for i, row in enumerate(rows):
    #         try:
    #             profilelink_tag = row.find_element_by_css_selector("div.ObjectCard-header > span > span > a.user")
    #             profilelink = profilelink_tag.get_attribute("href")
    #             self.logger.info(profilelink)
    #             button = row.find_element_by_css_selector("div.ObjectCard-footer > span > a.ui_button > div.ui_button_inner > div.ui_button_label_count_wrapper > span.ui_button_label")
    #             sleep(delay_random)
    #             if button.text=='Follow':
    #                 self.logger.info('Clicking {}'.format(button.text))
    #                 button.click()
    #                 followed = followed + 1
    #             else:
    #                 self.logger.info('Already {}'.format(button.text))
    #                 sleep(delay_random)
    #             if i>5:
    #                 self.browser.execute_script("window.scrollTo(0, " + str(int((i-2)/2)*ROW_HEIGHT) + ");")
    #         except Exception as e:
    #             self.logger.error(e)
    #             failed = failed + 1
    #             self.logger.info('Failed {} times'.format(failed))
    #             sleep(delay_random)
    #         if failed >= 6:
    #             self.logger.info('Failed too many times. Something is wrong. Returning')
    #             return
    #         self.logger.info('followed in this iteration till now: {}'.format(followed))
    #         if followed >= amount:
    #             self.logger.info('Followed too many times this hour. Returning')
    #             return
    #         self.logger.info("====")

    # def follow_user_followers(self, users, amount, sleep_delay=2):
    #     for i, user in enumerate(users):
    #         web_address_navigator(Settings, self.browser, "https://medium.com/profile/" + user + "/followers")
    #         self.logger.info('Browsing followers of {}'.format(user))
    #         self.follow_all_here(amount=amount, sleep_delay=sleep_delay)

    # def follow_user_following(self, users, amount, sleep_delay=2):
    #     for i, user in enumerate(users):
    #         web_address_navigator(Settings, self.browser, "https://medium.com/profile/" + user + "/following")
    #         self.logger.info('Browsing following of {}'.format(user))
    #         self.follow_all_here(amount=amount, sleep_delay=sleep_delay)

    # def get_profile_links_from_search(self, search_term):
    #     search_url = "https://www.medium.com/search?q=" + search_term + "&type=profile"
    #     web_address_navigator(Settings, self.browser, search_url)
    #     profiles = self.browser.find_elements_by_css_selector("span > span  > span > a.user")
    #     links = []
    #     for profile in profiles:
    #         try:
    #             links.append(profile.get_attribute('href'))
    #             self.logger.info(profile.get_attribute('href'))
    #         except Exception as e:
    #             self.logger.error(e)
    #     return links


    # def get_post_links_from_search(self, search_term):
    #     search_url = "https://www.medium.com/search?q=" + search_term + "&type=post"
    #     web_address_navigator(Settings, self.browser, search_url)
    #     posts = self.browser.find_elements_by_css_selector("div.board_item_title > span.inline_editor_value > a.BoardItemTitle")
    #     links = []
    #     for post in posts:
    #         try:
    #             links.append(post.get_attribute('href'))
    #             self.logger.info(post.get_attribute('href'))
    #         except Exception as e:
    #             self.logger.error(e)
    #     return links

    def live_report(self):
        """ Report live sessional statistics """

        self.logger.info('')

        stats = [self.followed]

        if self.following_num and self.followed_by:
            owner_relationship_info = (
                "On session start was FOLLOWING {} users"
                " & had {} FOLLOWERS"
                .format(self.following_num,
                        self.followed_by))
        else:
            owner_relationship_info = ''

        sessional_run_time = self.run_time()
        run_time_info = ("{} seconds".format(sessional_run_time) if
                        sessional_run_time < 60 else
                        "{} minutes".format(truncate_float(
                            sessional_run_time / 60, 2)) if
                        sessional_run_time < 3600 else
                        "{} hours".format(truncate_float(
                            sessional_run_time / 60 / 60, 2)))
        run_time_msg = "[Session lasted {}]".format(run_time_info)

        if any(stat for stat in stats):
            self.logger.info(
                "Sessional Live Report:\n"
                "\t|> FOLLOWED {} users  |  ALREADY FOLLOWED: {}\n"
                "\n{}\n{}"
                .format(self.followed,
                        owner_relationship_info,
                        run_time_msg))
        else:
            self.logger.info("Sessional Live Report:\n"
                            "\t|> No any statistics to show\n"
                            "\n{}\n{}"
                            .format(owner_relationship_info,
                                    run_time_msg))

    def end(self):
        """Closes the current session"""

        # IS_RUNNING = False
        close_browser(self.browser, False, self.logger)

        with interruption_handler():
            # write useful information
            # dump_follow_restriction(self.username,
            #                         self.logger,
            #                         self.logfolder)
            # dump_record_activity(self.username,
            #                      self.logger,
            #                      self.logfolder,
            #                      Settings)

            with open('{}followed.txt'.format(self.logfolder), 'w') \
                    as followFile:
                followFile.write(str(self.followed))

            # output live stats before leaving
            self.live_report()

            message = "Session ended!"
            highlight_print(Settings, self.username, message, "end", "info", self.logger)
            self.logger.info("\n\n")

    def run_time(self):
        """ Get the time session lasted in seconds """

        real_time = time.time()
        run_time = (real_time - self.start_time)
        run_time = truncate_float(run_time, 2)

        return run_time

@contextmanager
def smart_run(session):
    try:
        if session.login():
            yield
        else:
            print("Not proceeding as login failed")

    except (Exception, KeyboardInterrupt) as exc:
        if isinstance(exc, NoSuchElementException):
            # the problem is with a change in IG page layout
            log_file = "{}.html".format(time.strftime("%Y%m%d-%H%M%S"))
            file_path = os.path.join(gettempdir(), log_file)
            with open(file_path, "wb") as fp:
                fp.write(session.browser.page_source.encode("utf-8"))
            print("{0}\nIf raising an issue, "
                  "please also upload the file located at:\n{1}\n{0}"
                  .format('*' * 70, file_path))

        # provide full stacktrace (else than external interrupt)
        if isinstance(exc, KeyboardInterrupt):
            clean_exit("You have exited successfully.")
        else:
            raise

    finally:
        session.end()

