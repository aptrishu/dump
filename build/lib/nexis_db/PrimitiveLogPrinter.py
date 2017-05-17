import sys
import traceback
from contextlib import contextmanager
from datetime import datetime

from pyprint.ConsolePrinter import ConsolePrinter


class PrimitiveLogPrinter(ConsolePrinter):

    def __init__(self, parallel=False, timestamp_format="%X"):
        """
        :param parallel: Set to true for parallel execution.
        :param timestamp_format: The format string for the
                                 datetime.today().strftime(format) method.
        """
        ConsolePrinter.__init__(self)
        self.parallel = parallel
        self.timestamp_format = timestamp_format

    def log(self, *args, **kwargs):
        """
        Adds the date to the message.
        """
        self.print('['+datetime.today().strftime(self.timestamp_format)+']',
                   *args, **kwargs)

    def debug(self, *args, **kwargs):
        self.log('DEBUG:', *args, color='green', **kwargs)

    def warn(self, *args, **kwargs):
        self.log('WARNING:', *args, color='yellow', **kwargs)

    def err(self, *args, **kwargs):
        self.log('ERROR:', *args, color='red', **kwargs)

    @contextmanager
    def do_safe_action(self, action_description, except_message=None,
                       reraise=False):
        if not self.parallel:
            self.debug(action_description + '...', end='')
            sys.stdout.flush()
            try:
                yield
                self.print(' DONE', color='green')
            except BaseException as exception:
                self.print(' FAILED!', color='red')
                self.print('Error message: ',
                           except_message or
                           str(exception) + '\n' + traceback.format_exc(),
                           color='red')
                if reraise:
                    raise exception
        else:
            self.debug(action_description)
            try:
                yield
                self.debug(action_description, 'DONE')
            except BaseException as exception:
                self.err(action_description, 'FAILED',
                         (except_message or
                          str(exception)+'\n'+traceback.format_exc()))
                if reraise:
                    raise exception
