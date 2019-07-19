
from sys import platform
from os import environ as environmental_variables
from os.path import join as join_path
from os.path import exists as path_exists


class Settings:

    def localize_path(*args):
        """ Join given locations as an OS path """
        if environmental_variables.get("HOME"):
            path = join_path(environmental_variables.get("HOME"), *args)
            return path
        else:
            return None

    # locations
    log_location = localize_path("MediumPy", "logs")
    database_location = localize_path("MediumPy/db", "mediumpy.db")
    OS_ENV = ("windows" if platform == "win32"
        else "osx" if platform == "darwin"
        else "linux")

    specific_chromedriver = "chromedriver_{}".format(OS_ENV)
    chromedriver_location = localize_path("MediumPy", "assets", specific_chromedriver)
    if (not chromedriver_location or not path_exists(chromedriver_location)):
        chromedriver_location = localize_path("MediumPy", "assets", "chromedriver")

    # minimum supported version of chromedriver
    chromedriver_min_version = 2.36

    platform_name = "medium"

    # set a logger cache outside the MediumPy object to avoid
    # re-instantiation issues
    loggers = {}
    logger = None

    # set current profile credentials for DB operations
    profile = {"id": None, "name": None}

    # hold live Quota Supervisor configuration for global usage
    QS_config = {}

    # specify either connected locally or through a proxy
    connection_type = None

    # store user-defined delay time to sleep after doing actions
    action_delays = {}

    # store configuration of text analytics
    # meaningcloud_config = {}
    # yandex_config = {}

    # store the parameter for global access
    show_logs = None

    # store what browser the user is using, if they are using firefox it is
    # true, chrome if false.
    use_firefox = None
    IS_RUNNING = False

    WORKSPACE = {"name": "MediumPy", "path": environmental_variables.get("HOME")}

    DATABASE_LOCATION = localize_path("MediumPy", "db", "mediumpy.db")

    # followers_count_xpath = '//a[@name="Followers"]/span[2]'
    # following_count_xpath = '//a[@name="Following"]/span[2]'


