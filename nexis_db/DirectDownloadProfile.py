from selenium.webdriver.firefox.firefox_profile import FirefoxProfile


class DirectDownloadProfile(FirefoxProfile):
    """
    This is a profile for selenium to automatically store all downloads
    noninteractively.
    """

    def __init__(self, download_dir):
        FirefoxProfile.__init__(self)

        # use most recent download folder again
        self.set_preference("browser.download.folderList", 2)
        self.set_preference("browser.download.downloadDir", download_dir)
        self.set_preference("browser.download.defaultFolder", download_dir)
        self.set_preference("browser.download.dir", download_dir)
        self.set_preference("browser.download.useDownloadDir", True)
        self.set_preference("browser.download.manager.showWhenStarting", False)
        self.set_preference("browser.helperApps.neverAsk.saveToDisk",
                            "application/msword,text/html,text/plain")
        self.set_preference(
            "browser.download.manager.showAlertOnComplete", False)
        self.set_preference("browser.download.manager.showWhenStarting", False)
        self.set_preference("browser.download.panel.shown", False)
        self.set_preference("browser.download.useToolkitUI", True)
