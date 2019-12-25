"""
Script to export someone's audible library into a Google Sheet.

"""
import sys
import os
import time
import json
import logging
import configparser
from pathlib import Path
from datetime import datetime, timezone
from warnings import warn
import argparse
import audible

CONFIG_FILE_PATH = os.environ["HOME"] + "/.audible2sheet.ini"

GSHEET_LIBRARY_FILE_PATH  = os.environ["HOME"] + "/.gsheet_books.txt"

def convert_length_in_minutes_to_hr_min_str(length_minutes):
    """
    Convert minutes into something like 02h03m if given 123.

    Note that both hr and min are 0-padded
    """
    hour = length_minutes // 60
    minutes = length_minutes % 60

    return "%02dh%02dm" % (hour, minutes)


def convert_utc_time_to_ccyymmdd(utc_time):
    """
    Convert a UTC datetime like: 2019-06-30T23:58:29.551Z and convert time to a local time/date string: CCYYMMDD.
    """
    try:
        utc_datetime = datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%S.%f%z")
    except ValueError:
        try:
            utc_datetime = datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            warn("Unknow date format for: {}".format(utc_time))

    if utc_datetime:
        local_datetime = utc_datetime.replace(tzinfo=timezone.utc).astimezone(tz=None)
        ccyymmdd = local_datetime.strftime("%Y%m%d")
    else:
        # poor man handling of unknown format but assuming the format ccyy-mm-dd
        ccyymmdd = "".join([utc_time[0:4], utc_time[5:2], utc_time[8:2]])

    return ccyymmdd


def extract_authors_from_json_list_sting(json_list_str):
    """
    Audible provides a list of authors which might includes translators, foreword, adaptors and other contributors.

    Examples:
        [{'asin': 'B072549W28', 'name': 'Seth Stephens-Davidowitz'}, {'asin': None, 'name': 'Steven Pinker - foreword'}]
        [{'asin': 'B001H6UJO8', 'name': 'Andreas Eschbach'}, {'asin': None, 'name': 'Samuel Willcocks (translator)'}]
    Only keep the true authors and return them as a nice CSV string
    """
    if json_list_str:
        all_authors = json_list_str
        real_authors = []
        for author in all_authors:
            name = author["name"]
            if (" (" not in name) and (" - " not in name):
                real_authors.append(name)
        authors = ", ".join(real_authors)
    else:
        authors = "UNKNOWN AUTHOR"

    return authors


class AudibleClient:
    """
    Audible client session which can be created by either:
        * from an already saved session file
        * or by providing credentials
    """

    def __init__(
        self, email, password, locale="us", session_file="/tmp/audible_session_file.txt"
    ):
        self._email = email
        self._password = password
        self._locale = locale
        self._session_file = session_file

        if not os.path.exists(self._session_file) or self._has_session_expired():
            self._create_with_credentials()

        try:
            self._restore_from_session_file()
        except Exception as msg:  # pylint: disable=W0702
            print(f"Can't log into Audible: {msg}")

            # If that doesn't work, try logging in with credentials
            self._create_with_credentials()

    def _restore_from_session_file(self):
        # Try to restore session from file if possible
        try:
            auth = audible.FileAuthenticator(
                filename=self._session_file, locale=self._locale, 
                register=True
            )
            self._client = audible.AudibleAPI(auth)
        except Exception as msg:
            msg = f"Can't log into Audible using session file ({self._session_file}): {msg}"
            raise Exception(msg)

    def _has_session_expired(self):
        with open(self._session_file) as session_file:
            session = json.load(session_file)
            if "expires" in session:
                if session["expires"] == None or time.time() < session["expires"]:
                    return False
        logging.info("Session has expired")
        return True

    def _create_with_credentials(self):
        if self._email and self._password:
            try:
                logging.info("Creating session using login/password credentials")
                auth = audible.LoginAuthenticator(
                    self._email, self._password, locale=self._locale
                )
            except Exception as msg:
                print(f"Can't log into Audible using credentials: {msg}")
                raise
        else:
            raise Exception("Both email and password must be specified")

        # save session after initializing
        auth.to_file(self._session_file, encryption=False)
        self._client = audible.AudibleAPI(auth)

    def is_logged_in(self):
        """Check if an Audible connection has been sucessfully established."""
        return hasattr(self, "_client")

    def get(self, *args, **kwarg):
        """Run query and get results on Audible connection."""
        try:
            return self._client.get(*args, **kwarg)
        except:
            print("Failed to get data from Audible")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="""
Pull Audible library books and output them to the screen or to a Google Sheet.
If Google credentials aren't specified, it outputs the list of books to the screen/STDOUT "|"-separated
""",
    )
    parser.add_argument("-c", "--cfg_file", help="Configuation file", default=CONFIG_FILE_PATH)
    parser.add_argument(
        "-r",
        "--print_raw_data",
        help="Print the raw data as returned by Audible",
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Verbose output to show addditonal information",
        action="store_true",
    )
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    # Get the configration file information
    cfg_file = args.cfg_file
    cfg = configparser.ConfigParser()
    if not os.path.exists(cfg_file):
        raise Exception(f"The configuration file:{cfg_file} doesn't exist")
        
    cfg.read(cfg_file)

    # get and create the root dir if it doesn't already exist
    root_path = cfg.get('general', 'root_path')
    if not root_path.startswith("/"):
        root_path = os.environ["HOME"] + "/" + root_path
    if os.path.exists(root_path):
        if not os.path.isdir(root_path):
            warn(f"{root_path} exists but is not a directory")
    else:
        # make it visible to the creator of the directory only b/c it contains confidential information
        os.mkdir(root_path, 0o700)

    # Audible specific data
    audible_cfg          = cfg['audible_cfg']
    audible_email        = audible_cfg.get('email')
    audible_password     = audible_cfg.get('password')
    audible_locale       = audible_cfg.get('locale', 'us')
    audible_session_path = audible_cfg.get('session_file_path', 'audible_session.txt')
    audible_library_path = audible_cfg.get('library_file_path', 'audible_books.txt')
    audible_min_length   = int(audible_cfg.get('min_length', 5))
    content_type_to_omit = audible_cfg.get('content_type_to_omit', '').split(",")
    asins_to_omit        = audible_cfg.get('asins_to_omit', '').split(" ")
    # Massage the cfg as needed
    if not audible_session_path.startswith("/"):
        audible_session_path = root_path + "/" + audible_session_path
    if not audible_library_path.startswith("/"):
        audible_library_path = root_path + "/" + audible_library_path

    # Establish a client session with Audible
    audible_session = AudibleClient(audible_email, audible_password, audible_locale, audible_session_path)
    if not audible_session.is_logged_in():
        raise Exception("Failed to connect to Audible")

    # get list of books from Audible library
    # since there's no way to know how many books or pages of books, assume that it won't be more that 100*500
    books = []
    for page in range(1, 100):
        logging.info("Requesting page {}".format(page))
        library, response = audible_session.get(
            "library",
            num_results=500,  # get 500 items at a time
            page=page,
            response_groups="product_desc,contributors,product_attrs",
        )
        items = library["items"]
        if response and items:
            for item in items:
                if args.print_raw_data:
                    print(item)
                asin = item["asin"]
                length_min = item["runtime_length_min"]
                if (
                    (not item["content_type"] in content_type_to_omit) and 
                    (not asin                 in asins_to_omit) and
                    length_min >= audible_min_length
                ):
                    title = item["title"]
                    sub_title = item["subtitle"]
                    if sub_title:
                        title = title + ": " + sub_title

                    all_authors = item["authors"]
                    authors = extract_authors_from_json_list_sting(all_authors)

                    purchase_date_utc = item["purchase_date"]
                    purchase_date = convert_utc_time_to_ccyymmdd(purchase_date_utc)

                    length_hr_min = convert_length_in_minutes_to_hr_min_str(length_min)

                    books.append(
                        "|".join([asin, title, authors, length_hr_min, purchase_date])
                    )
        else:
            #        print("Done with getting the library")
            break
    if books:
        # write to file and output to screen
        with open(audible_library_path, 'w') as writer:
            # Note the header here that cannot change and is used as info key for each book
            header = "|".join(["ASIN", "TITLE", "AUTHORS", "DURATION", "PURCHASE_DATE"])
            writer.write(header+"\n")
            if not args.print_raw_data:
                print(header)
            for book in books:
                writer.write(book+"\n")
                if not args.print_raw_data:
                    print(book)
        nbooks = len(books)
        print(f"Saved {nbooks} Audible book in {audible_library_path}");

if __name__ == "__main__":
    main()
