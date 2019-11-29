"""
Script to export someone's audible library into a Google Sheet.

"""
import sys
import os
import time
import json
import logging
from datetime import datetime, timezone
from warnings import warn
import argparse
import audible

LOCALE_DEFAULT = "us"
SESSION_FILE_PATH_DEFAULT = os.environ["HOME"] + "/.audible_session"
CONTENT_TYPE_TO_OMIT = ("Speech", "Newspaper / Magazine")


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
    parser.add_argument("-e", "--email", help="Audible email/login")
    parser.add_argument("-p", "--password", help="Audible password (if not specified, you will be prompted for it)")
    parser.add_argument("-l", "--locale", help="Locale (region)", default=LOCALE_DEFAULT)
    parser.add_argument(
        "-s", "--session", help="Audible session file path", default=SESSION_FILE_PATH_DEFAULT
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

    if args.email and not args.password:
        # The email was specified but not the password and so need to prompt the user for the password
        password = input("Please enter your Audible password: ")
    else:
        password = args.password

    client = AudibleClient(args.email, password, args.locale, args.session)
    if not client.is_logged_in():
        raise Exception("Failed to connect to Audible")
        
    # get list of books from Audible library
    # since there's no way to know how many books or pages of books, assume that it won't be more that 1000*50
    books = []
    for page in range(1, 1000):
        logging.info("Requesting page {}".format(page))
        #        else:
        #            print(".", end=".", file=sys.stderr)

        library, response = client.get(
            "library",
            num_results=50,
            page=page,
            response_groups="product_desc,contributors,product_attrs",
        )
        items = library["items"]
        if response and items:
            for item in items:
                if (not item["content_type"] in CONTENT_TYPE_TO_OMIT) and (
                    item["runtime_length_min"] > 0
                ):
                    asin = item["asin"]
                    title = item["title"]
                    sub_title = item["subtitle"]
                    if sub_title:
                        title = title + ": " + sub_title

                    all_authors = item["authors"]
                    authors = extract_authors_from_json_list_sting(all_authors)

                    purchase_date_utc = item["purchase_date"]
                    purchase_date = convert_utc_time_to_ccyymmdd(purchase_date_utc)

                    length_min = item["runtime_length_min"]
                    length_hr_min = convert_length_in_minutes_to_hr_min_str(length_min)

                    books.append(
                        "|".join([asin, title, authors, length_hr_min, purchase_date])
                    )
        else:
            #        print("Done with getting the library")
            break
    if books:
        print("|".join(["ASIN", "title", "authors", "length_hh:mm", "purchase_date"]))
        for book in books:
            print(book)


if __name__ == "__main__":
    main()
