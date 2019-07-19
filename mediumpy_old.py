#!/usr/bin/python
# -*- coding: utf-8 -*-
# Author: Matt Flood

import pickle, os, random, sys, time, math
from sys import platform
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options  
from random import shuffle

os.environ["PATH"] = os.environ["PATH"] + ":./"

# Configure constants here
EMAIL = 'helpsocialbotspy@gmail.com'
PHONE = 'phone'
PASSWORD = 'PWd'
LOGIN_SERVICE = 'Google'
DRIVER = 'Chrome'
LIKE_POSTS = True
COMMENT_ON_POSTS = True
COMMENTS = ['Great read!', 'Good work keep it up!', 'Really enjoyed the article!', 'Very interesting!', '👍🏻', 'Nice post👌🏻']
ARTICLE_BLACK_LIST = ['Sex', 'Drugs', 'Child Labor']
TOPIC_LIST = [ "humor", "internet-culture", "podcasts", "social-media", "business", "design", "freelancing", "leadership", "marketing", "product-management", "productivity", "startups", "work", "blockchain", "cryptocurrency", "cybersecurity", "data-science", "gadgets", "ios-development", "javascript", "machine-learning", "programming", "software-engineering", "technology", "ux", "visual-design", "travel" ]
TAG_LIST = [ "aws", "serverless", "aws-lambda", "java", "javascript", "scala" ]
FOLLOW_USERS = True
UNFOLLOW_USERS = True
UNFOLLOW_USERS_BLACK_LIST = ['DontUnFollowMe']
USE_RELATED_TAGS = True
ARTICLES_PER_TAG = 250
VERBOSE = True
INVOKATION_FREQUENCY = 24 * 60 / 15 # every 15 minutes
ARTICLES_PER_DAY = 88 * INVOKATION_FREQUENCY
MAX_CLAPS_PER_DAY = 1000
MAX_COMMENTS_PER_DAY = 125
MAX_FOLLOWS_PER_DAY = 125
CLAPS_PROBABILITY = int(MAX_CLAPS_PER_DAY / ARTICLES_PER_DAY * 1000)
COMMENTS_PROBABILITY = int(MAX_COMMENTS_PER_DAY / ARTICLES_PER_DAY  * 1000)
FOLLOWS_PROBABILITY = int(MAX_FOLLOWS_PER_DAY / ARTICLES_PER_DAY * 1000)
followedUsersAmount = 0
SESSION_FILE = "/tmp/medium.session"

class MediumPy:
def launch_browser():
    print('Launching Chrome')
    options = Options()
    if platform == "darwin":
        return webdriver.Chrome("chromedriver-mac", options=options)
    else:
        options.add_argument("--headless")
        options.add_argument('--no-sandbox')
        options.add_argument('--single-process')
        options.add_argument('--disable-dev-shm-usage')
        options.binary_location = "headless-chromium-lambda"
        return webdriver.Chrome("chromedriver-lambda", options=options)

def SignInToService(browser):
    """
    Using the selenium browser passed and the config file login to Medium to
    begin the botting.
    browser: the selenium browser used to login to Medium.
    """
    if os.path.isfile(SESSION_FILE):
        print("Found session file %s" % SESSION_FILE)
        browser.get("https://medium.com")
        with open(SESSION_FILE, 'rb') as i:
            cookies = pickle.load(i)
            for cookie in cookies:
                browser.add_cookie(cookie)
        return True

    serviceToSignWith = LOGIN_SERVICE.lower()
    signInCompleted = False
    print('Signing in...')

    # Sign in
    browser.get('https://medium.com/m/signin?redirect=https%3A%2F%2Fmedium.com%2F')

    if serviceToSignWith == "google":
        signInCompleted = SignInToGoogle(browser)

    elif serviceToSignWith == "twitter":
        signInCompleted = SignInToTwitter(browser)

    elif serviceToSignWith == "facebook":
        signInCompleted = SignInToFacebook(browser)

    if signInCompleted:
        print("Saving cookies to session file %s" % SESSION_FILE)
        with open(SESSION_FILE, 'wb') as output:
            pickle.dump(browser.get_cookies(), output, pickle.HIGHEST_PROTOCOL)

    return signInCompleted


def SignInToGoogle(browser):
    """
    Sign into Medium using a Google account.
    browser: selenium driver used to interact with the page.
    return: true if successfully logged in : false if login failed.
    """

    signInCompleted = False

    try:
        browser.find_element_by_xpath('//button[contains(text(),"Sign in or sign up with email")]').click()
        browser.find_element_by_name('email').send_keys(EMAIL)
        browser.find_element_by_class_name('button--google').click()
        browser.find_element_by_id("next").click()
        time.sleep(3)
        browser.find_element_by_id('Passwd').send_keys(PASSWORD)
        browser.find_element_by_id('signIn').click()
        time.sleep(3)
        signInCompleted = True
    except:
        pass

    if not signInCompleted:
        try:
            browser.find_element_by_id("identifierNext").click()
            time.sleep(3)
            browser.find_element_by_name('password').send_keys(PASSWORD)
            browser.find_element_by_id('passwordNext').click()
            time.sleep(3)
            signInCompleted = True
        except:
            print("Problem logging into Medium with Google.")
            pass

    return signInCompleted


	def SignInToTwitter(browser):
	    """
	    Sign into Medium using a Twitter account.
	    browser: selenium driver used to interact with the page.
	    return: true if successfully logged in : false if login failed.
	    """

	    signInCompleted = False
	    try:
	        browser.find_element_by_class_name('u-accentColor--buttonNormal').click()
	        browser.find_element_by_class_name('js-twitterButton').click()

	        if not browser.find_element_by_xpath('//input[@id="username_or_email"]').is_displayed():
	            browser.find_element_by_xpath('//input[@id="allow"]').click()
	            time.sleep(3)
	            signInCompleted = True

	        else:
	            browser.find_element_by_xpath('//input[@id="username_or_email"]').send_keys(EMAIL)
	            browser.find_element_by_xpath('//input[@id="password"]').send_keys(PASSWORD)
	            browser.find_element_by_xpath('//input[@id="allow"]').click()
	            time.sleep(3)
	            signInCompleted = True

	        try:
	            if browser.find_element_by_xpath('//input[@id="challenge_response"]').is_displayed():
	                browser.find_element_by_xpath('//input[@id="challenge_response"]').send_keys(PHONE)
	                browser.find_element_by_xpath('//input[@id="email_challenge_submit"]').click()
	                time.sleep(3)
	        except:
	            pass
	    except Exception as err:
	        print("Problem logging into Medium with Twitter.", err)
	        pass

	    return signInCompleted


	def SignInToFacebook(browser):
	    """
	    Sign into Medium using a Facebook account.
	    browser: selenium driver used to interact with the page.
	    return: true if successfully logged in : false if login failed.
	    """

	    signInCompleted = False
	    try:
	        browser.find_element_by_class_name('button--facebook').click()
	        browser.find_element_by_xpath('//input[@id="email"]').send_keys(EMAIL)
	        browser.find_element_by_xpath('//input[@id="pass"]').send_keys(PASSWORD)
	        browser.find_element_by_xpath('//button[@id="loginbutton"]').click()
	        time.sleep(3)
	        signInCompleted = True
	    except:
	        print("Problem logging into Medium with Facebook.")
	        pass

	    return signInCompleted

	def MediumBot():
	    """
	    Start botting Medium
	    """

	    browser = launch_browser()
	    SignInToService(browser)

	    tagURLsQueued = []
	    tagURLsVisitedThisLoop = []

	    tagURLsQueued = ScrapeUsersFavoriteTagsUrls(browser)
	    while tagURLsQueued:
	        articleURLsQueued = []
	        shuffle(tagURLsQueued)
	        tagURL = tagURLsQueued.pop()
	        tagURLsVisitedThisLoop.extend(tagURL)
	        try:
	             # Note: This is dones this way to add some timing between liking and
	             # commenting on posts to throw any bot finder logic off
	             tagURLsQueued.extend(NavigateToURLAndScrapeRelatedTags(browser, tagURL, tagURLsVisitedThisLoop))
	             articleURLsQueued = ScrapeArticlesOffTagPage(browser)

	             while articleURLsQueued:
	                 articleURL = articleURLsQueued.pop()
	                 try:
	                     print("Tags in Queue: "+str(len(tagURLsQueued))+" Articles in Queue: "+str(len(articleURLsQueued)))
	                     LikeCommentAndFollowOnPost(browser, articleURL)
	                 except Exception as err:
	                     print("Failed for article " + articleURL, err)
	                     pass
	        except Exception as err:
	            print("Failed for tag " + tagURL, err)
	            pass

	def ScrapeUsersFavoriteTagsUrls(browser):
	    """
	    Scrape the urls for the user's favorite tags. We will use these to go off
	    when interacting with articles.
	    """

	    tagURLS = []
	    if len(TOPIC_LIST) > 0 or len(TAG_LIST) > 0:
	        for tag in TOPIC_LIST:
	            tagURLS.append("https://medium.com/topic/" + tag)
	        for tag in TAG_LIST:
	            tagURLS.append("https://medium.com/tag/" + tag)
	    else:
	        browser.get("https://medium.com/me/following/topics")
	        time.sleep(5)
	        print('Gathering your favorited tags')

	        try:
	            for div in browser.find_elements_by_class_name('js-sectionItem'):
	                for a in div.find_element_by_tag_name('a'):
	                    if a["href"] not in tagURLS:
	                        tagURLS.append(a.get_attribute("href"))
	                        if VERBOSE:
	                            print(a.get_attribute("href"))

	        except:
	            print('Exception thrown in ScrapeUsersFavoriteTagsUrls()')
	            pass

	    if not tagURLS or USE_RELATED_TAGS:

	        if not tagURLS:
	            print('No favorited tags found. Grabbing the suggested tags as a starting point.')

	        try:
	            for div in browser.find_elements_by_class_name('u-sizeFull'):
	                for a in div.find_elements_by_tag_name('a'):
	                    if a.get_attribute("href") not in tagURLS:
	                        tagURLS.append(a.get_attribute("href"))
	                        if VERBOSE:
	                            print(a.get_attribute("href"))
	        except:
	            print('Exception thrown in ScrapeArticlesOffTagPage()')
	            pass
	    print('')

	    return tagURLS


	def NavigateToURLAndScrapeRelatedTags(browser, tagURL, tagURLsVisitedThisLoop):
	    """
	    Navigate to the tag url passed. If the USE_RELATED_TAGS is set scrape the
	    related tags found as well.
	    tagURL: the tag page to navigate to before scraping urls
	    tagURLsVisitedThisLoop: tags we have aready visited.
	        Don't want to waste time viewing them twice in a loop.
	    return: list of other tag urls to add to navigate to and bot.
	    """

	    browser.get(tagURL)
	    tagURLS = []

	    if USE_RELATED_TAGS and tagURL:

	        print('Gathering tags related to : '+tagURL)

	        try:
	            for ul in browser.find_elements_by_class_name('tags--postTags'):
	                for li in ul.find_elements_by_tag_name('li'):

	                    a = li.find_element_by_tag_name('a')

	                    if 'followed' not in a.get_attribute('href') and a.get_attribute('href') not in tagURLsVisitedThisLoop:
	                        tagURLS.append(a.get_attribute('href'))

	                        if VERBOSE:
	                            print(a.get_attribute('href'))
	        except:
	            print('Exception thrown in NavigateToURLAndScrapeRelatedTags()')
	            pass
	        print('')

	    return tagURLS


	def ScrapeArticlesOffTagPage(browser):
	    """
	    Scrape articles to navigate to from the tag's url.
	    return: a list of article urls
	    """

	    articleURLS = []
	    print('Gathering your articles for the tag :'+browser.current_url)

	    for counter in range(1,math.ceil(ARTICLES_PER_TAG/30)):
	        ScrollToBottomAndWaitForLoad(browser)

	    try:
	        for a in browser.find_elements_by_xpath(('//h3/a')) + browser.find_elements_by_xpath('//div[contains(@class,"js-postArticle")]/*/a'):
	            if VERBOSE:
	                print(a.get_attribute("href"))
	            articleURLS.append(a.get_attribute("href"))
	    except Exception as err:
	        print('Exception thrown in ScrapeArticlesOffTagPage()', err)
	        pass
	    print('')

	    return articleURLS


	def LikeCommentAndFollowOnPost(browser, articleURL):
	    """
	    Like, comment, and/or follow the author of the post that has been navigated to.
	    browser: selenium browser used to find the like button and click it.
	    articleURL: the url of the article to navigate to and like and/or comment
	    """

	    browser.get(articleURL)

	    if browser.title not in ARTICLE_BLACK_LIST:

	        doFollowUser = FOLLOW_USERS and random.choice([True] * FOLLOWS_PROBABILITY + [False] * (1000 - FOLLOWS_PROBABILITY))
	        # slowly grow number of followings, by unfollowing 95% only
	        doUnFollowUser = UNFOLLOW_USERS and doFollowUser and FollowUser(browser) and random.choice([True] * 90 + [False] * 10)

	        ScrollToBottomAndWaitForLoad(browser)

	        if LIKE_POSTS:
	            if random.choice([True] * CLAPS_PROBABILITY + [False] * (1000 - CLAPS_PROBABILITY)):
	                LikeArticle(browser)

	        if COMMENT_ON_POSTS:
	            if random.choice([True] * COMMENTS_PROBABILITY + [False] * (1000 - COMMENTS_PROBABILITY)):
	                CommentOnArticle(browser)

	        # if we follow someone, let's unfollow someone
	        if doUnFollowUser:
	            UnFollowUser(browser)

	        print('')


	def LikeArticle(browser):
	    """
	    Like the article that has already been navigated to.
	    browser: selenium driver used to interact with the page.
	    """

	    likeButtonXPath = '//button[@aria-label="Clap"]'

	    try:
	        likeButton = browser.find_element_by_xpath(likeButtonXPath)
	        buttonStatus = "is-active" in likeButton.get_attribute("class")

	        if likeButton.is_displayed() and buttonStatus != True:
	            if VERBOSE:
	                print('Liking the article : \"'+browser.current_url+'\"')
	            likeButton.click()
	            if VERBOSE:
	                print('Liked the article : \"'+browser.current_url+'\"')
	        elif VERBOSE:
	            print('Article \"'+browser.current_url+'\" is already liked.')

	    except Exception as err:
	        if VERBOSE:
	            print('Exception thrown when trying to like the article: '+browser.current_url, err)
	        pass


	def CommentOnArticle(browser):
	    """
	    Comment on the article that has already been navigated to.
	    browser: selenium driver used to interact with the page.
	    """

	    # Determine if the account has already commented on the post.
	    usersName = browser.find_element_by_class_name('avatar').find_element_by_tag_name('img').get_attribute("alt")
	    alreadyCommented = False

	    try:
	        browser.find_element_by_xpath('//button[contains(text(),"Show all responses")]').click()
	        alreadyCommented = browser.find_element_by_xpath('//a[text()[contains(.,"'+usersName+'")]]').is_displayed()
	    except:
	        pass

	    #TODO Find method to comment when the article is not hosted on medium.com currently
	    #     found issues with the logic below when not on medium.com.
	    if 'medium.com' in browser.current_url:
	        if not alreadyCommented:

	            comment = random.choice(COMMENTS)

	            try:
	                if VERBOSE:
	                    print('Commenting \"'+comment+'\" on the article : \"'+browser.title+'\"')
	                try:
	                    browser.find_element_by_xpath('//button[@data-action="toggle-responses"]').click()
	                except:
	                    pass
	                browser.find_element_by_class_name('inlineEditor-placeholder"')
	                browser.find_element_by_class_name('inlineEditor-header').click()
	                browser.find_element_by_xpath('//div[@role="textbox"]').send_keys(comment)
	                time.sleep(20)
	                browser.find_element_by_xpath('//button[@data-action="publish"]').click()
	                time.sleep(5)
	            except Exception as err:
	                if VERBOSE:
	                    print('Exception thrown when trying to comment on the article: '+browser.current_url, err)
	                pass
	        elif VERBOSE:
	            print('We have already commented on this article: '+browser.title)
	    elif VERBOSE:
	        print('Cannot comment on an article that is not hosted on Medium.com')


	def FollowUser(browser):
	    """
	    Follow the user whose article you have already currently navigated to.
	    browser: selenium webdriver used to interact with the browser.
	    """

	    try:
	        print('Following the user: '+browser.find_element_by_xpath('//a[@rel="author cc:attributionUrl"]').get_attribute("href"))
	        browser.find_element_by_xpath('//button[@data-action="toggle-subscribe-user"]').click()
	        return True
	    except Exception as err:
	        if VERBOSE:
	            print('Exception thrown when trying to follow the user.', err)
	        pass
	        return False

	def UnFollowUser(browser):
	    """
	    UnFollow a just from your followed user list.
	    browser: selenium webdriver used to interact with the browser.
	    Note: view the black list of users you do not want to unfollow.
	    """

	    browser.get('https://medium.com/me')
	    time.sleep(3)

	    browser.get(browser.current_url + "/following")
	    time.sleep(3)

	    try:
	        followedUsers = browser.find_elements_by_xpath('//a[@data-action="show-user-card"]')
	        random.shuffle(followedUsers)

	        for followedUser in followedUsers:
	            followedUserUrl = followedUser.get_attribute("href")
	            if not any(blackListUser in followedUserUrl for blackListUser in UNFOLLOW_USERS_BLACK_LIST):
	                browser.get(followedUserUrl)
	                break

	        time.sleep(3)
	        print('UnFollow the user: '+browser.current_url)
	        print('')
	        browser.find_element_by_xpath('//button[contains(text(),"Following")]').click()

	    except Exception as err:
	        if VERBOSE:
	            print('Exception thrown when trying to unfollow a user.', err)
	        pass

	def ScrollToBottomAndWaitForLoad(browser):
	    """
	    Scroll to the bottom of the page and wait for the page to perform it's lazy laoding.
	    browser: selenium webdriver used to interact with the browser.
	    """

	    browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
	    time.sleep(4)

if __name__ == '__main__':
    MediumBot()
