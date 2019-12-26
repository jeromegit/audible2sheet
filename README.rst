audible2sheet: your Audible library in a Google sheet!
======================================================

Script to export the list of books in one's Audible library into a Google Sheet document

It uses `mkb79's excellent Audible API <https://github.com/mkb79/Audible>`_.

Requirements
------------

- Python >= 3.6
- depends on following packages:

  - audible
  - pygsheets

Installation
------------
``pip install audible2sheet``

If you want to save your library to a Google Sheet, you need to follow:
 #. `Turn on the Google Sheets API <https://developers.google.com/sheets/api/quickstart/python#step_1_turn_on_the>`_.
 #. You need to provide a spreadsheetId:
   
   #. Go to your `Google Sheets <https://docs.google.com/spreadsheets/u/0/>`_
   #. Create a new spreadsheet
   #. Once/if you have a spreadsheet, go to it and note the **spreadsheetId** in the URL in your browser:
      https://docs.google.com/spreadsheets/d/**1iDrHMdst9zVyQJltBUiAvuc7E_bk37Nb0MFOw5jD3zo**/edit#gid=0

Configuration
--------------
Since there are so many things that you can tweak in terms of configuration, I decided to put all that information in a configuration file instead of passing the configuration as CLI arguments

Unless specified otherwise using -c /some/other/path, the configuration file is expected to be in your homedir (~) as .audiblesheet.ini.

I provide a sample of a cfg file in audible2sheet.ini_ORIG that looks like this::

    [general]
    root_path = .audible2sheet
    # root_path = /Users/user_name/.audible2sheet

    [audible_cfg]
    # MANDATORY
    email = xxx@yyy.com
    # Not mandatory but you will be prompted for it if not specified
    password = MyK0mplXPasswd
    # Can be changed but are defaulted to the below values
    session_file_path = audible_session.txt
    # Check out the Localizations section in this page: https://github.com/mkb79/Audible
    locale = us
    library_file_path = audible_books.txt
    # Minimum length (in minutes) to be kept in the library
    min_length = 1
    # ASINS to omit in case you don't want publically show that you like the Twilight series ;-)
    # (space-separated)
    asins_to_omit =
    # Audible content to ignore (comma-separated)
    # Find available choices here: https://www.audible.com/advsr under Program Type
    # Based on my own list showing that "Product" (Audiobook?) is the most prevalent
    # Episode                 1
    # Lecture                15
    # Newspaper / Magazine    2
    # Performance            12
    # Product               602
    # Radio/TV Program        5
    # Show                    1
    # Speech                  6
    content_type_to_omit = Speech,Newspaper / Magazine
    
    [google_sheet_cfg]
    creds_file_path = audible2googlesheet.json
    sheet_name = my_audible_books_generated_by_audible2sheet
    cache_file_path = gsheet_books.txt

So, ``cp audible2sheet.ini_ORIG ~/.audible2sheet.ini; chmod 600 ~/.audible2sheet.ini`` and then at the very least specify your email audible email in the audible_cfg section.
If you don't want to be prompted each time, also specify your password.

If you are not in the US, change the locale as well. Check out the Localizations section in this page: https://github.com/mkb79/Audible


Authentication
==============
Audible Configuration
---------------------
In order to access your Audible library, you need to provide login and password (see configuration above) to the script in order to log in on your behalf.
The first time you do this, you will be challenged with a CAPTCHA image that looks like this:

.. image:: captcha_sample.png

and prompted at the command line with:

``Answer for CAPTCHA:``
   
(Note that you might be prompted more than once if you answer incorrectly)

Once the CAPTCHA has been successfully verified, your access is granted and your session is saved in your ~/.audible2sheet/audible_session.txt file unless specified otherwise in the configuration file.

Finally, your locale ("us" by default) can be specified if you live outside the US.
Check out the Localizations section in this page: https://github.com/mkb79/Audible

Once your session has been established you no longer need to specify your email or password until the session expires. It seems to expire after few hours at this point.


Google Sheets Configuration
---------------------------

Follow the instructions here:
https://pygsheets.readthedocs.io/en/stable/authorization.html
(More specifically the top of the "Authorizing pygsheets" section)

Then the "Service Account" section which is what is used in this in Audible2sheet:
https://pygsheets.readthedocs.io/en/stable/authorization.html#service-account

The downloaded .json file must be placed here ``~/.audible2sheet/audible2googlesheet.json`` unless specified otherwise in the configuration file.


Usage
-----
Just print the list of books to the screen:

``audible2sheet.py``

If you don't specify your Audible password in the cfg file, you will be prompted for it with:

``Please enter your Audible password:``

You can redirect it to a file of your choosing

``audible2sheet.py > audible_books.txt``

Notes
-----
I'm purposely omitting "books" that have a zero-length and "books" of type "Speech" and "Newspaper / Magazine".

That can be tweaked in the configuration file.


✨🍰✨
