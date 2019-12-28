#!/usr/bin/env python3
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
import csv
import audible
import pygsheets
from collections import defaultdict

# Some constants
CONFIG_FILE_PATH = os.environ['HOME'] + '/.audible2sheet.ini'
AUDIBLE_FILE_PATH_DEFAULT = 'audible_books.txt'
AUDIBLE_RAW_FILE_PATH_DEFAULT = 'audible_raw_books.txt'
GSHEET_FILE_PATH_DEFAULT  = 'gsheet_books.txt'

# Book Class
class Book:
    """
    Book class
    """
    FIELD_NAME_ASIN          = 'ASIN'
    FIELD_NAME_TITLE         = 'TITLE'
    FIELD_NAME_AUTHORS       = 'AUTHORS'
    FIELD_NAME_DURATION      = 'DURATION'
    FIELD_NAME_PURCHASE_DATE = 'PURCHASE_DATE'
    FIELD_NAMES = [
        FIELD_NAME_ASIN,
        FIELD_NAME_TITLE,
        FIELD_NAME_AUTHORS,
        FIELD_NAME_DURATION,
        FIELD_NAME_PURCHASE_DATE,
    ]
    UNKNOWN_VALUE            = '???'
    def __init__(self, asin, title, authors, duration, purchase_date):
        self.asin            = asin
        self.title           = title
        self.authors         = authors
        self.duration        = duration
        self.purchase_date   = purchase_date

    @classmethod
    def book_from_dict(cls, book_dict):
        """
        Create a book out of a dictionary of book "fields"
        """
        book_params = []
        # make sure that all required fields are present
        for field in Book.FIELD_NAMES:
            if field in book_dict:
                value = book_dict[field]
                if not value or value.isspace():
                    warn(f"Invalid value:{value} associated with field:{field} in book dictionary:{book_dict}")
                    value = Book.UNKNOWN_VALUE
            else:
                warn(f"Can't find field:{field} in book dictionary:{book_dict}")
                value = Book.UNKNOWN_VALUE
            book_params.append(value)

        try:
            book = cls(*book_params)
            return book
        except Exception as error:
            warn(f"Can't create a book with book dictionary:{book_dict} because {error}")
            return None

    def book_to_dict(self):
        """
        Create dictionary of field=value pairs from a book
        """
        book_dict = {
            Book.FIELD_NAME_ASIN:self.asin,
            Book.FIELD_NAME_TITLE:self.title,
            Book.FIELD_NAME_AUTHORS:self.authors,
            Book.FIELD_NAME_DURATION:self.duration,
            Book.FIELD_NAME_PURCHASE_DATE:self.purchase_date,            
            }
                     
        return book_dict

    def __repr__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )


# Useful functions to convert time and date formats
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
            print(f"Can't log into Audible: {msg}", file=sys.stderr)

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
                print(f"Can't log into Audible using credentials: {msg}", file=sys.stderr)
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
            print("Failed to get data from Audible", file=sys.stderr)


def create_books_dict_from_file(file):
    """
    Create a list of books dict using ASIN as key from a "|"-separated file
    """
    books_dict = dict()
    with open(file, 'r', newline='') as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter='|')
        for book_dict in csv_reader:
            book = None
            if Book.FIELD_NAME_ASIN in book_dict:
                asin = book_dict[Book.FIELD_NAME_ASIN]
                if asin and not asin.isspace():
                    book = Book.book_from_dict(book_dict)
            if book:
                books_dict[asin] = book

    return books_dict


def get_gs_wks(gs_cfg, root_path):
    """
    Get a Google Sheet API handle to get/set worksheet data
    """
    # GS cfg data
    creds_file_path = create_full_path(gs_cfg.get('creds_file_path'), root_path)
    sheet_name      = gs_cfg.get('sheet_name', 'my_audible_books_generated_by_audible2sheet')
    gs_email        = gs_cfg.get('email')
    
    gc = pygsheets.authorize(service_file=creds_file_path)
    try: 
        sheet = gc.open(sheet_name)
    except pygsheets.SpreadsheetNotFound as error:
        # Can't find it and so create it
        res = gc.sheet.create(sheet_name)
        sheet_id = res['spreadsheetId']
        sheet = gc.open_by_key(sheet_id)
        print(f"Created spreadsheet with id:{sheet.id} and url:{sheet.url}")

        # Share with self to allow to write to it
        sheet.share(gs_email, role='writer', type='user')

        # Share to all for reading
        sheet.share('', role='reader', type='anyone')
    wks = sheet.sheet1

    return wks


def get_gs_books_and_save_to_file(wks, gs_library_path):
    """
    Get the data from the GoogleSheet or create the sheet if it doesn't already exist
    Return the list of cols in the header
    """
    gs_rows = wks.get_all_values(include_tailing_empty_rows=False)

    gs_header_cols = gs_rows[0]
    if all(s == '' or s.isspace() for s in gs_header_cols):
        # There's no header yet and so initialize it with some default including freezing the header
        gs_header_cols = Book.FIELD_NAMES
        wks.insert_rows(0, values=[gs_header_cols])
        wks.frozen_rows = 1

    with open(gs_library_path, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter='|')
        csv_writer.writerows(gs_rows)
    print(f"Saved {len(gs_rows)} books in {gs_library_path}", file=sys.stderr)

    return gs_header_cols


def get_new_book_rows(audible_books, gs_books, gs_header_cols):
    """
    Go over all the Audible books to see if any new were added vs the GS list of books
    The ASIN is used as a key to map books in Audible and GS
    The user might have added new columns and suffled in the order of the columns; we should respect that
    """
    new_book_rows = []
    for asin, audible_book in audible_books.items():
        if not asin in gs_books:
            book_dict = audible_book.book_to_dict()
            new_row_cols = []
            for gs_field in gs_header_cols:
                if gs_field in book_dict:
                    field_value = book_dict[gs_field]
                    # Special case with ASIN where leading zeroes would be stripped otherwise
                    if field_value.startswith("0"):
                        # prefix with a leading ' to tell GS not to strip the leasing zeros
                        field_value = "'"+field_value
                else:
                    field_value = ""
                new_row_cols.append(field_value)
            new_book_rows.append(new_row_cols)
            print(f"ADD: {audible_book}", file=sys.stderr)

    return new_book_rows


def insert_new_book_row_to_gs_wks(wks, new_book_rows):
    print(f"Need to insert {len(new_book_rows)} new books/rows...", file=sys.stderr)
    wks.insert_rows(1, number=len(new_book_rows), values=new_book_rows)

    
def create_full_path(path, root_path):
    """ 
    check if a path is absolute
    if absolute return as-is, otherwise return root_path/path
    """
    if os.path.isabs(path):
        return path
    else:
        return root_path + "/" + path
    

def get_audible_books_and_save_to_file(audible_cfg, root_path):
    """
    Use the Audible API to get the list of all books from Audible and save the list 
    """
    # Audible cfg data
    audible_email            = audible_cfg.get('email')
    audible_password         = audible_cfg.get('password')
    audible_locale           = audible_cfg.get('locale', 'us')
    audible_session_path     = create_full_path(audible_cfg.get('session_file_path', 'audible_session.txt'), root_path)
    audible_library_path     = create_full_path(audible_cfg.get('library_file_path', AUDIBLE_FILE_PATH_DEFAULT), root_path)
    audible_raw_library_path = create_full_path(audible_cfg.get('raw_library_file_path', AUDIBLE_RAW_FILE_PATH_DEFAULT), root_path)
    audible_min_length       = int(audible_cfg.get('min_length', 5))
    content_type_to_omit     = audible_cfg.get('content_type_to_omit', '').split(",")
    asins_to_omit            = audible_cfg.get('asins_to_omit', '').split(" ")

    # Establish a client session with Audible
    audible_session = AudibleClient(audible_email, audible_password, audible_locale, audible_session_path)
    if not audible_session.is_logged_in():
        raise Exception("Failed to connect to Audible")

    # get list of books from Audible library
    # since there's no way to know how many books or pages of books, assume that it won't be more that 100*500
    books = []
    with open(audible_raw_library_path, 'w') as raw_writer:
        for page in range(1, 100):
            print(f"Requesting Audible page #{page}...", file=sys.stderr)
            library, response = audible_session.get(
                "library",
                num_results=500,  # get 500 items at a time
                page=page,
                response_groups="product_desc,contributors,product_attrs",
            )
            items = library["items"]
            if response and items:
                for item in items:
                    raw_writer.write(json.dumps(item)+"\n")
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
        # write to cache file
        with open(audible_library_path, 'w') as writer:
            # Note the header here that cannot change and is used as info key for each book
            header = "|".join(Book.FIELD_NAMES)
            writer.write(header+"\n")
            for book in books:
                writer.write(book+"\n")
        print(f"Saved {len(books)} Audible book in {audible_library_path}", file=sys.stderr);

def print_raw_data_fields_list(raw_library_file_path):
    fields = defaultdict(int) 
    with open(raw_library_file_path, 'r') as raw_file:
        for json_raw_book in raw_file:
            book_as_dict = (json.loads(json_raw_book))
            for field in book_as_dict.keys():
                fields[field] += 1
    for field in sorted(fields):
        print(field)

        
def print_file_as_is(file_to_print):
    with open(file_to_print, 'r') as file:
        print(file.read())

        
def print_specified_field_from_raw_file(raw_file_path, specified_fields):
    header = "|".join(specified_fields)
    print(header)
    with open(raw_file_path, 'r') as raw_file:
        for json_raw_book in raw_file:
            book_as_dict = (json.loads(json_raw_book))
            columns = []
            for field in specified_fields:
                if field in book_as_dict and book_as_dict[field] is not None:
                    if field == 'authors' or field == 'narrators':
                        # Special case of authors and narrators which ate actually json lists and not simple strings
                        col_value = extract_authors_from_json_list_sting(book_as_dict[field])
                    else:
                        col_value = str(book_as_dict[field])
                else:
                    col_value = '???'
                columns.append(col_value)
            print("|".join(columns))
                
    
# --------------------------------------------------------------------------------
def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="""
Pull Audible library books and output them to the screen or to a Google Sheet.
The list of books to the screen/STDOUT is "|"-separated
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
        "-R",
        "--print_specific_raw_data",
        help="Print the specified raw data column (space-separated) as returned by Audible",
    )
    parser.add_argument(
        "-l",
        "--list_raw_data_fields",
        help="List all the raw data fields as returned by Audible",
        action="store_true",
    )
    parser.add_argument(
        "-g",
        "--google_sheet_export",
        help="Export the Audible book list to the Google Sheet specified in the configuration file.",
        action="store_true",
    )
    parser.add_argument(
        "-a",
        "--use_audible_cache_file",
        help="Use Audible cache file instead of requesting the data",
        action="store_true",
    )
    parser.add_argument(
        "-A",
        "--use_audible_raw_cache_file",
        help="Use Audible raw cache file instead of requesting the data",
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

    # Get/save/print Audible books
    audible_cfg = cfg['audible_cfg']
    if not (args.use_audible_cache_file or args.use_audible_raw_cache_file):
        get_audible_books_and_save_to_file(audible_cfg, root_path)
    if args.list_raw_data_fields:
        raw_library_file_path = create_full_path(audible_cfg.get('raw_library_file_path', AUDIBLE_RAW_FILE_PATH_DEFAULT), root_path)
        print_raw_data_fields_list(raw_library_file_path)
    else:
        if args.print_raw_data or args.print_specific_raw_data:
            raw_library_file_path = create_full_path(audible_cfg.get('raw_library_file_path', AUDIBLE_RAW_FILE_PATH_DEFAULT), root_path)
            if args.print_raw_data:
                print_file_as_is(raw_library_file_path)
            else:
                specified_fields = args.print_specific_raw_data.split(" ")
                print_specified_field_from_raw_file(raw_library_file_path, specified_fields)
        else:
            library_file_path = create_full_path(audible_cfg.get('library_file_path',     AUDIBLE_FILE_PATH_DEFAULT),     root_path)
            print_file_as_is(library_file_path)

    # Get/save GoogleSheet (GS) books
    if args.google_sheet_export:
        gs_cfg = cfg['google_sheet_cfg']
        gs_wks = get_gs_wks(gs_cfg, root_path)
        gs_library_path = create_full_path(gs_cfg.get('library_file_path', GSHEET_FILE_PATH_DEFAULT), root_path)
        gs_header_cols = get_gs_books_and_save_to_file(gs_wks, gs_library_path)

        # Load lists of books from files into dictionaries for an easy 1x1 comparison based on ASIN
        audible_books = create_books_dict_from_file(audible_library_path)
        gs_books      = create_books_dict_from_file(gs_library_path)

        # Create new rows based on the delta between audible and gs and the header columns
        new_book_rows = get_new_book_rows(audible_books, gs_books, gs_header_cols)

        # insert
        if len(new_book_rows):
            insert_new_book_row_to_gs_wks(gs_wks, new_book_rows)
        else:
            print("No new books found", file=sys.stderr)

if __name__ == "__main__":
    main()
