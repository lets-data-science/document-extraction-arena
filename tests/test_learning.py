import math
from decimal import Decimal
import pytest
from learner.normalize import to_decimal
from learner.matching import match_rows
from learner.report import summarize
from runner.score import score_line_items, money_equal, parse_response
from runner.validation import validate_invoice, validate_image, load_json


def item(qty=1,amount=100,label='Consulting'):
    return {'description':label,'quantity':qty,'unit_price':100,'amount':amount}

@pytest.mark.parametrize('value',[None,True,False,'NaN','Infinity',float('nan'),float('inf'),'$13','12,34',{},[], '1e999'])
def test_normalize_rejects_invalid_amounts(value):assert to_decimal(value) is None

def test_normalize_preserves_scientific_notation():
    assert to_decimal('1e3')==Decimal('1000')
    assert not money_equal('1e3',13)
    assert money_equal(12.341,12.34)
    assert not money_equal(12.345,12.34)

def test_matching_repeated_descriptions_remain_distinct():
    expected=[item(),item(2,200)]
    assert match_rows(expected,list(reversed(expected)))==[(0,1),(1,0)]
    assert score_line_items(expected,list(reversed(expected)))[0]==1

def test_matching_cannot_award_one_row_twice():
    assert score_line_items([item(),item()],[item(),item(label='Invented')])[0]==.5

def test_matching_empty_cases_are_explicit():
    assert score_line_items([],[])[0]==1
    assert score_line_items([item()],[])[0]==0
    assert score_line_items([],[item()])[0]==0

def test_matching_handles_overlapping_tolerances():
    a=item(amount=100);b=item(amount=100.008)
    x=item(amount=100.004);y=item(amount=99.999)
    assert len(match_rows([a,b],[x,y]))==2

def test_report_requires_every_field():
    report=summarize(dict(zip('abcdefgh',[1]*7+[.5])))
    assert report['correct']==7 and report['exact'] is False
    assert report['mean']==.9375
    assert summarize(dict(zip('abcdefgh',[1]*8)))['exact'] is True
    with pytest.raises(ValueError):summarize({})
    with pytest.raises(ValueError):summarize(dict(zip('abcdefgh',[float('nan')]*8)))

@pytest.mark.parametrize('value',['{"total": NaN}','{"line_items": null}', '[]'])
def test_invalid_truth_is_rejected(value):
    with pytest.raises(ValueError):validate_invoice(load_json(value))

def test_malformed_prediction_and_image_do_not_crash_scorer():
    assert parse_response('{"total": NaN}') is None
    assert parse_response('{"line_items": [{"description": "Missing money"}]}') is None
    with pytest.raises(ValueError):validate_image(b'not an image')
