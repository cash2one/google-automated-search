import bs4
import datetime
import math
import logging
import os.path
import random
import requests
import time
import urllib
from fake_useragent import UserAgent

# Setup logging for console display
logging.basicConfig(
    format="%(message)s",
    level=logging.INFO
)

# Setup global variables
MIN_WAIT = 10
MAX_WAIT = 15
INPUT_FILENAME = 'Queries.txt'
OUTPUT_FILENAME = 'Results.csv'
N_RESULTS = 50
MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December"
]
DATE_NOW = datetime.datetime.now().date()
BASE_URL = "https://www.google.com/search"


##### High-level search-related methods #####


def safely_search_and_save(n, queries, date):
    """Safely searches google for the first n results for each query
    using the specified date in the search. Results are saved afterwards."""
    count = len(queries)
    for i in range(count):
        query = queries[i]
        search_and_save(n, query, date)
        if i + i < count:
            logging.info("\nWaiting a few seconds...\n")
            wait_random()


def search_and_save(n, query, date):
    """Searches google for the first n results for 'RFP "{query}" {date}'.
    Results are saved afterwards."""
    queried_on = DATE_NOW
    search_term = get_search_string(query, date)
    results = get_first_n_results(n, search_term)
    full_results = map(lambda r :
        (search_term, date.strftime("%Y %m"), queried_on.strftime("%Y %m"), r[0], r[1], r[2], checked_url(r[3])),
        results)
    logging.info("Saving results")
    append_results(full_results)


def get_first_n_results(n, search_term):
    """Searches google for the first n results for a particular search term and returns
    a list of (rank, title, url)."""
    safe_n = get_safe_n(n)
    parameters = get_params(safe_n, search_term)
    logging.info("Searching for : %s" % search_term)
    html = search(BASE_URL, parameters)
    parser = bs4.BeautifulSoup(html, "html.parser")
    results = list()
    item_containers = parser.select(".g")
    for c in item_containers:
        data = c.select("h3.r")
        if (len(data)) == 0:
            continue
        item = data[0]
        heading_data = item.select("a")[0]
        title = heading_data.getText()
        raw_url = heading_data.get("href")
        url = clean_url(raw_url)
        summary = get_summary(c)
        print(summary)
        if title and url:
            results.append((len(results)+1, title, summary, url))
        if len(results) == n:
            break
    return results


def search(url, params=None):
    """Searches a url with given query-string parameters and returns the html."""
    full_url = url
    if params is not None:
        param_key_values = list(params.items())
        query_string = "".join(map(lambda p: "&%s=%s" % p, param_key_values))
        if len(query_string) != 0:
            query_string = "?" + query_string
        full_url = url + query_string
    logging.debug("full url : %s" % full_url)
    response = requests.get(full_url, headers=get_random_headers())
    response.raise_for_status()
    return response.text


##### Low-level user-logic functions #####


def get_random_headers():
    """Gets random headers to query google with."""
    headers = {
        "User-Agent": UserAgent().ie
    }
    logging.debug(headers)
    return headers


def checked_url(string):
    """Checks for valid URL and returns result."""
    if len(string) > 255:
        return "ERROR"
    return string


def get_summary(container):
    """Gets the summary of a Google result"""
    summary = None
    res = container.select(".st")
    if len(res) > 0:
        summary = res[0].getText()
        summary = summary.replace("\n", " ")
    return summary


def clean_url(href):
    """Cleans a href found from the result item heading."""
    logging.info("before: " + href)
    href = urllib.parse.unquote(href)
    if href.startswith("/search"):
        return None
    query_start = href.find("?")
    url_start = href.find("?url=")
    url_type = href.startswith("/url")
    if url_start >= 0:
        href = href[url_start + 5:]
        if url_type:
            param_start = href.find("&")
            href = href[:param_start]

    #href = href[start:]  # remove preceding '/url?q=' , etc
    logging.info("after: " + href)
    logging.info("")
    return href


def get_safe_n(n):
    """Inflates the number of results shown as some returned are 'improprer'."""
    if n < 10:
        n += 5
    n = math.ceil(1.2 * n)
    return n


def get_params(count, query):
    """Gets the google query-string parameters."""
    params = {
        "num": count,   # results per page
        "q": query      # search term
    }
    return params


def append_results(results):
    """Appends the results to the results file."""
    if not os.path.isfile(OUTPUT_FILENAME):
        create_results_file()
    file = open_when_free(OUTPUT_FILENAME, 'a')
    for result in results:
        logging.debug(result)
        file.write('%s,%s,%s,%s,"%s","%s","=HYPERLINK(""%s"")"\n' % result)
    file.close()


def create_results_file():
    """Creates new results file with headers."""
    file = open_when_free(OUTPUT_FILENAME, 'w')
    file.write("QueryTotal,QueryDate,QueriedOn,Rank,Title,Summary,Url\n")
    file.close()


def read_queries():
    """Reads the strings from the input file and returns them."""
    with open(INPUT_FILENAME) as file:
        queries = [line.strip() for line in file.readlines()]
    return queries


def get_search_string(query, date):
    """Given a query and date, this returns a string 'RFP "{query}" {date}'."""
    return '%s %s' % (query, date.strftime("%B %Y"))


def get_date():
    """Gets the date from the user either using today's date or user-defined."""
    print("How would you like to choose a date?")
    mode = get_int_input_in_range("Current date (1) or Manual selection (2)?", 1, 2)
    if mode == 1:
        return DATE_NOW
    elif mode == 2:
        months_ind_val = list(enumerate(MONTHS, start=1))
        month_str_lines = map(lambda x: "(%2s) %s" % (x[0], x[1]), months_ind_val)
        months_disp = "\n".join(month_str_lines)
        month = get_int_input_in_range("Choose a month:\n" + months_disp, 1, 12)
        year = get_int_input("Enter a year:")
        return datetime.date(year, month, 1)


##### Utility Functions #####


def get_int_input_in_range(prompt, min, max):
    """Requests a integer input between min and max."""
    print(prompt)
    while True:
        answer = get_int_input()
        if not (min <= answer <= max):
            print("Error: Digit not in range")
            continue
        return answer


def get_int_input(prompt=None):
    """Requests an integer input."""
    if prompt is not None:
        print(prompt)
    while True:
        answer = input("> ")
        if not answer.isdigit():
            print("Error: Not a digit")
            continue
        return int(answer)


def wait_random():
    """Waits a random time between min and max."""
    wait_time = random.randrange(MIN_WAIT, MAX_WAIT)
    logging.debug("Waiting %s seconds" % wait_time)
    time.sleep(wait_time)


def open_when_free(filename, mode):
    """Opens file for writing and waits for the resource to be freed. The file handler is returned."""
    while True:
        try:
            file = open(filename, mode, encoding='utf-8')
            return file
        except PermissionError:
            logging.info("Error: Cannot open %s as it is in use by another process. Please close the file." % filename)
            logging.info("Please close the file and press ENTER when you have done so.")
            input("")


#### MAIN STARTER #####

if __name__ == "__main__":

    # Introduction
    print("Google Automated Search")
    print("By David Button")
    print("For Ian\n")

    # Get manual or automatic date
    date = get_date()

    # Read rfp queries from file
    rfp_queries = read_queries()
    logging.info("Found %s queries\n" % len(rfp_queries))
    logging.debug(rfp_queries)

    # Safely search and save the results
    safely_search_and_save(N_RESULTS, rfp_queries, date)

    # Finish
    logging.info("\nSearching complete!")
