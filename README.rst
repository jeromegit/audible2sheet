audible2sheet: your Audible library in a Google sheet!
======================================================

Script to export the list of books in one's Audible library into a Google Sheet document

It uses `mkb79's Audible API <https://github.com/mkb79/Audible>`_.

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
 - `step 1: Turn on the Google Sheets API <https://developers.google.com/sheets/api/quickstart/python#step_1_turn_on_the>`_.
 - You need to provide a spreadsheetId:
   
   - Go to your `Google Sheets <https://docs.google.com/spreadsheets/u/0/>`_
   - Create a new spreadsheet
   - Once/if you have a spreadsheet, go to it and note the **spreadsheetId** in the URL in your browser:
     https://docs.google.com/spreadsheets/d/**1iDrHMdst9zVyQJltBUiAvuc7E_bk37Nb0MFOw5jD3zo**/edit#gid=0

Authentication
--------------
In order to access your Audible library, you will need 
Usage
-----
Just print the list of books to the screen:
``audible2sheet.py -e myemail@company.com -p MyK0mplXPasswd``
  

Notes
-----
I'm purposely omitting "books" that have a zero-length and "books" of type "Speech" and "Newspaper / Magazine"

✨🍰✨
