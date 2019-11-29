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

Authentication
--------------
In order to access your Audible library, you need to provide login and password to the script in order to log in on your behalf.
The first time you do this, you will be challenged with a CAPTCHA image that looks like this:

.. image:: captcha_sample.png

and prompted at the command line with:

``Answer for CAPTCHA:``
   
(Note that you might be prompted more than once if you answer incorrectly)

Once the CAPTCHA has been successfully verified, your access is granted and your session is saved in your homedir's .audible_session file unless specified otherwise with -s file_path
Finally, your locale ("us" by default) can be specified if you live outside the US.

Once your session has been established you no longer need to specify your email or password until the session expires. It seems to expire after 24 hours at this point.


Usage
-----
Just print the list of books to the screen:

``audible2sheet.py -e myemail@company.com [-p MyK0mplXPasswd]``

If you don't specify -p password, you will be prompted for it with:

``Please enter your Audible password:``

It's actually safer to not specify it at the command line as shell history will reveal it to prying eyes.
  

Notes
-----
I'm purposely omitting "books" that have a zero-length and "books" of type "Speech" and "Newspaper / Magazine"

✨🍰✨
