import re
from contextlib import contextmanager
from datetime import date, timedelta
from os import listdir, path, unlink
from random import random
from shutil import rmtree
from tempfile import mkdtemp
from time import sleep

from pyprint.ClosableObject import ClosableObject
from pyvirtualdisplay.display import Display
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select

from nexis_db.Article import Article
from nexis_db.DirectDownloadProfile import DirectDownloadProfile
from nexis_db.PrimitiveLogPrinter import PrimitiveLogPrinter


class ServerError(Exception):
    pass


@contextmanager
def open_nexis_db(user, password, hide_window=True):
    nexis = Nexis(user, password, hide_window)
    try:
        yield nexis
    finally:
        nexis.close()


class TooManyResults(Exception):
    pass


class Nexis(ClosableObject):
    """
    The actual Nexis database wrapper. It fetches data from the Uni Hamburg
    nexis database via selenium.
    """

    COUNT_REGEX = re.compile(r"([0-9]+) Dokument.* und ([0-9]+) Duplikat.*")

    def __init__(self, user, password, hide_window=True,
                 printer=PrimitiveLogPrinter(),
                 ignore_big_queries=True):
        """
        Creates a new database proxy.

        :param user: User name.
        :param password: Password.
        :param hide_window: Wether or not to show the browser window (showing
                            might be useful for debugging.)
        :param printer: A PrimitiveLogPrinter which will be used for indicating
                        actions and logging.
        :param ignore_big_queries: If set to True, queries resulting in more
                                   than 3000 results will be ignored.
        """
        ClosableObject.__init__(self)

        # If an exception occurs later those members have to exist for _close()
        self.browser = None
        self.display = None
        self.tempdir = None

        # For (primitive) logging
        self.printer = printer

        self.ignore_big_queries = ignore_big_queries

        self.user = user
        self.password = password
        if hide_window:
            with self.printer.do_safe_action(
                    'Starting virtual display',
                    "Browser window cannot be hidden. You might need to "
                    "install Xvfb. Continuing with visible browser window."):
                self.display = Display(visible=0)
                self.display.start()

        self.tempdir = mkdtemp()
        self.browser = webdriver.Firefox(DirectDownloadProfile(self.tempdir))

        # Retrieve token for this session

        with self.printer.do_safe_action('Authenticating at Nexis',
                                         reraise=True):
            self.authenticate()
            sleep(5)
            self.browser.find_element_by_xpath(
                '//a[@title="Profisuche"]').click()
            sleep(10 + random()*5)

        self.home_url = self.browser.current_url

    def authenticate(self):
        self.browser.get(
                "http://rzblx10.uni-regensburg.de/dbinfo/warpto.php?bib_id="
                "sub_hh&color=2&titel_id=1670&url=http%3A%2F%2Femedien.sub."
                "uni-hamburg.de%2Fhan%2Flexis")
        sleep(5 + random()*5)

        self.browser.find_element_by_name('User').send_keys(self.user)
        self.browser.find_element_by_name('Password').send_keys(self.password)
        self.browser.find_element_by_name("submitimg").click()

        # accept the terms, if required
        try:
            sleep(10 + random()*5)
            self.browser.find_element_by_css_selector(
                "a[href^='/auth/submitterms.do']").click()
        except NoSuchElementException:
            pass

        # Press ok on relogin prompt if needed
        try:
            sleep(5 + random()*5)
            self.browser.find_element_by_xpath(
                '//td/input[@title="OK"]').click()
            self.printer.debug("Relogin needed for {}. Executed successfully."
                               .format(self.user))
        except NoSuchElementException:
            pass
        

    def query(self, search_term: str, from_date: date=None, to_date: date=None,
              languages: str='us', company_canonical_name=' '):
        """
        Performs a query to the NexisLexis database.

        :param search_term: The search term.
        :param from_date:   Lower date limit.
        :param to_date:     Upper date limit.
        :param languages:   One of "all", "german", "english" or "us".
        """
        with self.printer.do_safe_action(
                "Querying for '{}'".format(search_term), reraise=True):
            if self.browser.current_url != self.home_url:
                self.browser.get(self.home_url)

            from_date = from_date or date(2005, 1, 1)
            to_date = to_date or date.today()

            # Fill and submit query
            self._fill_query_data(search_term, from_date, to_date, languages)
            sleep(5 + random()*5)
            self.browser.find_element_by_css_selector(
                    "img[title='Suche']").click()
            sleep(5 + random()*5)

            if self._no_results:
                return []

            if self.too_many_results:
                if self.ignore_big_queries:
                    return {'error': 'Too many results (>3000)',
                            'error_code': 1}

                self.printer.debug("Number of results for query '{}' exceeds "
                                   "3000. The query will be split.".format(
                                       search_term))
                # Split up logarithmically
                middle = from_date + (to_date-from_date)/2
                one_after_middle = middle + timedelta(days=1)
                results = self.query(search_term, from_date, middle,company_canonical_name=company_canonical_name)
                results += self.query(search_term, one_after_middle, to_date,company_canonical_name=company_canonical_name)
                return results

            return self._get_results(company_canonical_name, search_term)

    def element_exists_by_xpath(self, path):
        try:
            element = self.browser.find_element_by_xpath(path)
            return element
        except NoSuchElementException:
            return None

    @property
    def _no_results(self):
        return (self.element_exists_by_xpath("//h1[@class='zeroMsgHeader']")
                is not None)

    def _get_results(self, company_canonical_name, search_term):
        def press_forward():
            """
            Presses the forward button so lexisnexis updates the document count.
            """
            try:
                self.browser.find_element_by_xpath(
                    '//div/ol/li[@class="last"]/a').click()
            except:
                pass

        def get_document_count():
            """
            Retrieves the document count. Though it might raise over time when
            LexisNexis decides to analyze more documents.
            """
            sleep(10)
            count_text = self.browser.find_element_by_xpath(
                "//div/dl/dd[last()]").text
            try:
                matches = self.COUNT_REGEX.search(count_text).groups()
            except AttributeError:
                # The one result case
                return 1

            documents = int(matches[0])
            duplicates = int(matches[1])
            return documents-duplicates

        results = []

        # Give nexis some time for duplication analysis
        sleep(10)
        press_forward()

        document_count = get_document_count()

        downloaded_documents = 0
        while downloaded_documents < document_count:
            batch_start = downloaded_documents + 1
            batch_end = min(downloaded_documents + 200, document_count)
            results += self._download_results(batch_start, batch_end, company_canonical_name, search_term)
            sleep(2)
            downloaded_documents = batch_end
            if len(results) != downloaded_documents:
                print("Got", len(results), "results, expecting",
                      downloaded_documents, "instead.")

            # Updates document count, lexis will do that on the server while
            # were already downloading stuff
            press_forward()
            document_count = get_document_count()

        return results

    def _download_results(self, batch_start, batch_end, company_canonical_name, search_term, retry=3):
        def download_in_progress():
            # if found a file without .part extension then we're done
            for file_ in listdir(self.tempdir):
                if ".part" in file_:
                    return True
                else:
                    return False
            # No files at all? Download hasn't started yet.
            return True

        # Open Download Popover, it'll have three "tabs" with options
        self.browser.find_element_by_id("delivery_DnldRender").click()
        sleep(5 + random()*5)

        # First tab: range and full text

        # Range field won't be there for only one document, selection irrelevant
        if not (batch_start == 1 == batch_end):
            range_text = "{}-{}".format(batch_start, batch_end)
            self.browser.find_element_by_id("sel").click()
            self.browser.find_element_by_id(
                "rangetextbox").send_keys(range_text)

            # full text with indexing
            Select(self.browser.find_element_by_name(
                "delView")).select_by_index(3)

        # Switch to tab 2: deactivate cover page
        self.browser.find_element_by_xpath("//div/ul/li/a["
                                           "@href='#tabs-2']").click()
        if self.browser.find_element_by_id("cvpg").is_selected():
            self.browser.find_element_by_id("cvpg").click()

        # Switch to tab 3: download as txt, ignore the rest (not applicable
        # to txt)
        self.browser.find_element_by_xpath("//div/ul/li/a["
                                           "@href='#tabs-3']").click()
        Select(self.browser.find_element_by_id("delFmt")).select_by_index(3)

        # Actually click Download
        self.browser.find_element_by_class_name("deliverBtn").click()

        while True:
            close_btn = self.element_exists_by_xpath("//*[@id='closeBtn']")
            if close_btn is not None:
                # Download is started, click the OK button to close popover
                close_btn.click()
                break

            partial_content = self.element_exists_by_xpath(
                "//h1[text()=\"Partial Content\"]")
            arbitrary_error = self.element_exists_by_xpath(
                "//span[text()=\"Fehler bei der Anfrage\"]")
            if (partial_content or arbitrary_error) is not None:
                sleep(5)
                for elem in self.browser.find_elements_by_xpath(
                        "//a/span[text()='close']"):
                    try:
                        elem.click()
                        break
                    except:
                        pass
                else:
                    raise RuntimeError("Closing the window impossible")

                sleep(2 + random()*5)

                if retry == 0:
                    raise ServerError("Unable to fetch data.")

                # Retry
                return self._download_results(batch_start, batch_end, company_canonical_name, search_term,
                                              retry=retry-1)

            # Do not busy loop the whole time
            sleep(1)

        sleep(1)
        while download_in_progress():
            sleep(1)

        sleep(1)
        with open(path.join(self.tempdir, listdir(self.tempdir)[0]),
                  'r') as file:
            content = file.read()
            articles = list(Article.from_nexis_text(content, company_canonical_name, search_term))

        for file in listdir(self.tempdir):
            unlink(path.join(self.tempdir, file))

        return articles

    @property
    def too_many_results(self):
        try:
            container = self.browser.find_element_by_css_selector(
                    '#popupContainer')
            container.find_element_by_css_selector("span.l0")
            return True
        except NoSuchElementException:
            return False

    def _fill_query_data(self, search_term, from_date, to_date, languages):
        """
        Fills the search form with the given data.
        """
        #wait = WebDriverWait(self.browser, 10)
        #term_input = wait.until(self.browser.find_element_by_name("searchTermsTextArea"))
        #confirm.click()
        sleep(10)
        term_input = self.browser.find_element_by_name("searchTermsTextArea")
        term_input.clear()
        term_input.send_keys('"' + search_term + '"')

        language_value_dict = {
            'all': 'All English and German Language News',
            'english': 'All English Language News',
            'german': 'German Language News',
            'us': 'US Publications'}

        source_term = language_value_dict.get(languages, 'US Publications')
        self.browser.find_element_by_xpath("//div[@rel='more_sources']").click()
        # Activate JS in the text field
        self.browser.find_element_by_id('selected_source').send_keys('')
        sleep(5 + random() * 5)
        self.browser.find_element_by_id('selected_source').send_keys(
            source_term)
        # Page needs some time to show autocompletion box
        sleep(10 + random() * 5)
        self.browser.find_element_by_id('selected_source').send_keys(
            Keys.ARROW_DOWN)
        self.browser.find_element_by_id('selected_source').send_keys(
            Keys.ENTER)

        date_selector = self.browser.find_element_by_name("dateSelector")

        '''
        # select custom date
        Select(date_selector).select_by_index(11)
        date_selector.send_keys(Keys.ENTER)

        from_date_field = self.browser.find_element_by_name("fromDate")
        from_date_field.clear()
        from_date_field.send_keys(from_date.strftime('%d/%m/%Y'))

        to_date_field = self.browser.find_element_by_name("toDate")
        to_date_field.clear()
        to_date_field.send_keys(to_date.strftime('%d/%m/%Y'))
        '''

        # Filter group duplicates
        if not self.browser.find_element_by_name("gDuplicates").is_selected():
            self.browser.find_element_by_name("gDuplicates").click()
        # Set group duplicate filter to "similar"
        self.browser.find_element_by_id('duplicatesModal').click()
        try:
            self.browser.find_element_by_xpath(
                "//input[@value='search.common.threshold.broadrange']").click()
        except:
            pass

        self.browser.find_element_by_id('saveBooksBtn').click()

        if not self.browser.find_element_by_name(
                "excludeObituariesChecked").is_selected():
            self.browser.find_element_by_name(
                    "excludeObituariesChecked").click()

    def _close(self):
        with self.printer.do_safe_action('Cleaning up'):
            if self.browser is not None:
                self.browser.quit()
            if self.display is not None:
                self.display.stop()
            if self.tempdir:
                rmtree(self.tempdir, ignore_errors=True)
