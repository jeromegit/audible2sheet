import pytest
import sys
import warnings
from audible2sheet.audible2sheet import *

def test_main_cached_raw_specified_fields_filtered_by_asin(capsys):
    sys.argv = ['', '-A', '-R', 'title authors category_ladders series', '-f', 'B002V5CO3I']
    main()
    captured = capsys.readouterr()
    assert captured.out == """title|authors|category_ladders|series
Song of Susannah|Stephen King|Fiction / Horror|The Dark Tower
"""

def test_main_cached_raw_specified_fields(capsys):
    sys.argv = ['', '-A', '-R', 'title authors category_ladders series']
    main()
    captured = capsys.readouterr()
    output = captured.out
    nlines = output.count('\n')
    assert nlines > 600

def test_convert_length_in_minutes_to_hr_min_str():
    assert convert_length_in_minutes_to_hr_min_str(123) == "02h03m"
    assert convert_length_in_minutes_to_hr_min_str(0)   == "00h00m"
    assert convert_length_in_minutes_to_hr_min_str()    == "00h00m"

def test_convert_utc_time_to_ccyymmdd_with_valid_utc_format():
    assert convert_utc_time_to_ccyymmdd("2019-06-30T23:58:29.551Z") == "20190630"
    assert convert_utc_time_to_ccyymmdd("2019-06-30T23:58:29Z")     == "20190630"
    
def test_convert_utc_time_to_ccyymmdd_with_invalid_utc_format(recwarn):
    assert convert_utc_time_to_ccyymmdd("2019-06-30") == "20190630"
    assert len(recwarn) == 1
    w = recwarn.pop(UserWarning)
    assert issubclass(w.category, UserWarning)
    assert str(w.message) == "Unknown date format for: 2019-06-30"
    
def test_convert_utc_time_to_ccyymmdd_with_empty_value(recwarn):
    assert convert_utc_time_to_ccyymmdd("")  == ""
    assert len(recwarn) == 1
    w = recwarn.pop(UserWarning)
    assert issubclass(w.category, UserWarning)
    assert str(w.message) == "Unknown date format for: "

def test_convert_utc_time_to_ccyymmdd_with_missing_value(recwarn):
    assert convert_utc_time_to_ccyymmdd()  == ""
    assert len(recwarn) == 1
    w = recwarn.pop(UserWarning)
    assert issubclass(w.category, UserWarning)
    assert str(w.message) == "Unknown date format for: "

def test_extract_authors_from_json_data():
    assert extract_authors_from_json_data([{'asin': 'B072549W28', 'name': 'Seth Stephens-Davidowitz'},
                                           {'asin': None, 'name': 'Steven Pinker - foreword'}]) \
                                           == 'Seth Stephens-Davidowitz'
    assert extract_authors_from_json_data([{'asin': 'B001H6UJO8', 'name': 'Andreas Eschbach'},
                                           {'asin': None, 'name': 'Samuel Willcocks (translator)'}]) \
                                           == 'Andreas Eschbach'
    assert extract_authors_from_json_data([{"asin": "B000AQ0AWW", "name": "Douglas Preston"},
                                           {"asin": "xxxx",       "name": "Jerome Bogus - me"},
                                           {"asin": "B000APYNUI", "name": "Lincoln Child"}]) \
                                           == 'Douglas Preston, Lincoln Child'
    assert extract_authors_from_json_data('') == 'UNKNOWN AUTHOR'
    assert extract_authors_from_json_data()   == 'UNKNOWN AUTHOR'

