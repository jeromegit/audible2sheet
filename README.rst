audible2sheet: your Audible library in a Google sheet!
======================================================

Script to export the list of books in one's Audible library into a Google Sheet document

It uses `mkb79's Audible API <https://github.com/mkb79/Audible>`_.

Requirements
------------

- Python >= 3.6
- depends on following packages:

  - audible

Installation
------------
``pip install audible2sheet``

If you want to save your library to a Google Sheet, you need to follow `step 1: Turn on the Google Sheets API <https://developers.google.com/sheets/api/quickstart/python#step_1_turn_on_the>`_.

Usage
-----
Just print the list of books to the screen:
  ``audible2sheet.py -e myemail@company.com -p MyK0mplXPasswd``

✨🍰✨
