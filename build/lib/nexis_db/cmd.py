import csv
import json
from argparse import ArgumentParser
from configparser import ConfigParser
from os import makedirs, mkdir
from os.path import exists, expanduser, join

from nexis_db.JSONEncoder import JSONEncoder
from nexis_db.ParallelNexis import do_parallel_queries

CONFIGDIR = join(expanduser('~'), '.config', 'LexisNexisCrawler')
makedirs(CONFIGDIR, exist_ok=True)
CONFIGFILE = join(CONFIGDIR, 'users')


def create_crawler_argparser():
    parser = ArgumentParser()
    parser.add_argument('QUERY_FILE', help="Input file containing the queries. "
                                           "(A CSV file.)")
    parser.add_argument('OUTPUT', help="Output directory. All retrieved data "
                                       "will be written as JSON files here.")
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Show the browser window to follow the progress.')
    parser.add_argument("-j", "--jobs", type=int,
                        help="Number of jobs to use in parallel. There will "
                             "never be more jobs used than user data sets "
                             "available!")
    parser.add_argument("-l", "--limit-jobs", type=int,
                        help="Limit the number of queries to the given number.")
    parser.add_argument("-b", "--download-big-queries", action='store_true',
                        help="If set, big queries (>3000 results) will also "
                             "be downloaded.")
    return parser


def csv_rows(filename):
    with open(filename, 'r', errors='ignore', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            yield row


def get_new_queries(filename, output_dir, limit):
    """
    Reads queries from the CSV, checks wether they're already downloaded on
    the filesystem and yields them only if they are not.

    :param filename:
    :param output_dir: The directory where the JSON files can be found.
    """
    for row in csv_rows(filename):
        if not exists(query_to_filename(output_dir, row['name'])):
            yield row

            if limit is not None:
                limit -= 1
                if limit == 0:
                    break


def query_to_filename(dir: str, search_term: str):
    return join(dir, search_term.replace(' ', '_').replace('/', '_')+'.json')


def write_json(filename, result):
    with open(filename, 'w') as fileh:
        json.dump(result, fileh, cls=JSONEncoder, indent=1)


def main():
    args = create_crawler_argparser().parse_args()
    parser = ConfigParser()
    parser.read(CONFIGFILE)
    user_dict = dict(parser['userdata'])

    try:
        mkdir(args.OUTPUT)
    except FileExistsError:
        pass

    for name, result in do_parallel_queries(
            list(get_new_queries(args.QUERY_FILE, args.OUTPUT,
                                 args.limit_jobs)),
            args.jobs,
            user_dict,
            not args.debug,
            ignore_big_queries=not args.download_big_queries):
        write_json(query_to_filename(args.OUTPUT, name), result)
