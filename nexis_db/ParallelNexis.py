"""
Contains a class and utilities that allow to do multiple queries to the nexis
db in parallel.
"""
from datetime import datetime
from multiprocessing import Process, Queue, cpu_count
from multiprocessing.queues import Empty

from nexis_db.nexis import Nexis
from nexis_db.PrimitiveLogPrinter import PrimitiveLogPrinter


def get_cpu_count():
    try:
        return cpu_count()
    # cpu_count is not implemented for some CPU architectures/OSes
    except NotImplementedError:  # pragma: no cover
        return 2


def do_parallel_queries(rows: list, job_count: int, user_dict: {str: str},
                        hide=True, ignore_big_queries=True):
    """
    Yields name, results for successful queries.

    :param rows:      The CSV rows (dict) to query
    :param job_count: Number of processes to launch
    :param user_dict: A dictionary holding usernames as keys and passwords as
                      values.
    :param hide:      Whether or not to show the actual browser windows.
    """
    job_count = min(job_count or get_cpu_count(), len(rows), len(user_dict))
    task_queue = Queue()
    for row in rows:
        task_queue.put((0, row))

    result_queue = Queue()
    users = list(user_dict.keys())
    processes = [Worker(task_queue, result_queue,
                        users[i], user_dict[users[i]], hide,
                        ignore_big_queries=ignore_big_queries)
                 for i in range(0, job_count)]
    for process in processes:
        process.start()

    for i in range(0, len(rows)):
        retval = result_queue.get()
        if retval is None:  # This one went wrong :(
            continue
        name, result = retval
        if type(result) != dict:
            print('['+str(i+1)+'/'+str(len(rows))+']', "Got",
                  len(result), "results for", name)
        else:
            print('['+str(i+1)+'/'+str(len(rows))+']',
                  'Got no results for', name, ' (too many).')
        yield name, result

    # Join *after* getting queues, otherwise deadlock
    for process in processes:
        process.join()


class Worker(Process):

    def __init__(self, task_queue, result_queue, user, password, hide=True,
                 ignore_big_queries=True):
        Process.__init__(self)
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.hide = hide
        self.user = user
        self.password = password
        self.ignore_big_queries = ignore_big_queries

    def run(self):
        printer = PrimitiveLogPrinter(True)
        nexis = Nexis(user=self.user, password=self.password,
                      hide_window=self.hide, printer=printer,
                      ignore_big_queries=self.ignore_big_queries)
        try:
            while True:
                attempt, row = self.task_queue.get(timeout=1)
                name = row['name']
                try:
                    from_date = datetime.strptime(row['from date'], '%d-%m-%Y')
                    to_date = datetime.strptime(row['to date'], '%d-%m-%Y')
                except:
                    from_date, to_date = None, None
                languages = row.get('languages', 'us')
                if attempt > 2:
                    printer.err("Maximum attempts for task", name,
                                "exceeded. Dropping.")
                    self.result_queue.put(None)
                    continue
                try:
                    company_canonical_name = row['company canononical name']
                except:
                    company_canonical_name = None
                try:
                    result = nexis.query(name, from_date, to_date, languages,company_canonical_name=company_canonical_name)
                    self.result_queue.put((name, result))
                except:
                    printer.warn("Error while querying for", name,
                                 ". Restarting query later...")
                    nexis.close()
                    nexis = Nexis(user=self.user, password=self.password,
                                  hide_window=self.hide, printer=printer)
                    self.task_queue.put((attempt+1, row))
        except Empty:
            pass
        finally:
            nexis.close()
