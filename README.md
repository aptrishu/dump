Lexis Nexis Crawler
===================

Configuration
-------------

0. Download and extract the LexisNexisCrawler, either via
<https://gitlab.com/TUHH-TIE/LexisNexisCrawler/repository/archive.zip?ref=master>
   or clone the Git repository.
1. Install firefox
2. Install the requirements: `python3 -m pip install -r requirements.txt`
3. Install the crawler: `python3 setup.py install` (on linux, prefix `sudo`)
4. Add your user data: `python3 configure_user_data.py`, the script will
   guide you through it.
5. Follow http://stackoverflow.com/a/40208762/3212182

Usage
-----

2. Export your queries to a .csv file. Your query has to be in a column with the
   title `name`. Other recognized column names are `from date`, `to date` (in
   the format `DD-MM-YYYY`) and `languages` (one of `us` (default) `all`,
   `german` or `english`, only `us` is well tested though, others might yield
   errors and need adaption).
3. Simply invoke `crawl_nexis.py <your_csv_file.csv> <output_dir>`
4. Your data will be fetched and written into the output directory you specified as
   JSON files.

An example CSV file is given with `example.csv`. The `test.csv` contains some
larger query set useful for debugging.

### Large Datasets

Some queries are resulting in a large number of datasets. Those are by default
ignored and will not be reattempted. Such a query will result in a JSON file
like this:

```json
{
 "error_code": 1,
 "error": "Too many results (>3000)"
}
```

So if you want to further want to work with the data you can just look into
the JSON error code to determine if the data was downloaded correctly.

If you want the crawler to download even big datasets, pass the `-b` argument.

Resources
=========

 * https://www.lexisnexis.com/webserviceskit/v2_0beta/text/WSK-Operations.aspx
 * https://hkn.eecs.berkeley.edu/~dhsu/hacks.shtml
