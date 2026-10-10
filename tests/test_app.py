"""User-flow regression checks. Every provider call is mocked; tests spend no quota."""
import json
import io
import sys
from pathlib import Path
from unittest import mock
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runner'))
import run_models

@pytest.fixture
def no_api():
    with mock.patch.object(run_models, 'make_client', side_effect=AssertionError('API client created')) as mk, mock.patch.object(run_models, 'extract', side_effect=AssertionError('API request made')) as ex:
        yield mk, ex

def load(view=None):
    at = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30)
    if view: at.session_state['view'] = view
    return at.run()

def markdown(at): return ' '.join(m.value for m in at.markdown)

def live(at): return at.radio(key='workflow').set_value('New extraction').run()

def fake_result(text=None,error=None):
    return dict(response_text=text,seconds=1.5,input_tokens=1000,output_tokens=500,thinking_tokens=0,error=error)

def click_run(monkeypatch,result):
    monkeypatch.setenv('GEMINI_API_KEY','test-key-not-real')
    with mock.patch.object(run_models,'make_client',return_value=object()), mock.patch.object(run_models,'extract',return_value=result) as ex:
        at=live(load()); at.button[0].click().run()
    return at,ex

def test_saved_replay_is_key_free_and_defaults_to_a_real_mismatch(no_api):
    at=load()
    assert not at.exception
    assert at.selectbox(key='saved_invoice').value == 'level4_hard_014'
    assert '7 of 8' in markdown(at)
    assert '2026-08-03' in markdown(at) and '2026-03-08' in markdown(at)
    assert len(at.text_input)==0
    for call in no_api: call.assert_not_called()

def test_switch_model_and_filter_use_saved_evidence(no_api):
    at=load(); at.selectbox(key='saved_model').set_value('gemini-3.6-flash').run()
    assert not at.exception and '8 of 8' in markdown(at)
    at.radio(key='saved_filter').set_value('Differences only').run()
    assert any('No mismatches' in x.value for x in at.success)

def test_comparison_uses_the_same_invoices(no_api):
    at=load('Compare models')
    assert not at.exception
    text=markdown(at)
    assert '11<span> / 16' in text and '15<span> / 16' in text
    assert any('not a production accuracy ranking' in c.value for c in at.caption)

def test_comparison_download_works_without_generated_summary(no_api):
    original_read_csv = pd.read_csv
    def read_source(path, *args, **kwargs):
        assert Path(path).name != 'summary_same_invoices.csv', 'Generated summaries are not required by a clean clone'
        return original_read_csv(path, *args, **kwargs)
    with mock.patch.object(pd, 'read_csv', side_effect=read_source), mock.patch('streamlit.download_button', return_value=False) as download:
        at = load('Compare models')
    assert not at.exception
    download.assert_called_once()
    exported = original_read_csv(io.StringIO(download.call_args.args[1])).set_index('model')
    assert set(exported.index) == {'gemini-3.1-flash-lite', 'gemini-3.6-flash'}
    assert exported['n'].tolist() == [16, 16]
    assert exported.loc['gemini-3.1-flash-lite', 'exact_invoice_pct'] == 68.75
    assert exported.loc['gemini-3.6-flash', 'exact_invoice_pct'] == 93.75

def test_live_perfect_answer_and_only_one_request(monkeypatch):
    at,ex=click_run(monkeypatch,fake_result((ROOT/'examples/samples/sample_01.json').read_text()))
    assert not at.exception
    ex.assert_called_once(); assert ex.call_args.kwargs['no_retry'] is True
    assert '8 of 8' in markdown(at)
    assert any('Actual charges depend on your account' in c.value for c in at.caption)

@pytest.mark.parametrize('error,phrase',[('HTTP_429','quota limit'),('HTTP_503','busy'),('HTTP_403','permissions')])
def test_live_errors_are_actionable(monkeypatch,error,phrase):
    at,_=click_run(monkeypatch,fake_result(error=error))
    assert not at.exception and any(phrase in e.value for e in at.error)

def test_invalid_response_is_not_awarded_a_score(monkeypatch):
    at,_=click_run(monkeypatch,fake_result('{"total":NaN}'))
    assert not at.exception
    assert any('No score was awarded' in w.value for w in at.warning)

def test_missing_key_never_makes_a_request(no_api,monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    at=live(load());at.button[0].click().run()
    assert not at.exception and any('No request was made' in i.value for i in at.info)
    for call in no_api:call.assert_not_called()

def test_typed_key_is_used_but_not_rendered(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    with mock.patch.object(run_models,'make_client',return_value=object()) as mk, mock.patch.object(run_models,'extract',return_value=fake_result((ROOT/'examples/samples/sample_01.json').read_text())):
        at=live(load());at.text_input(key='api_key_input').set_value('session-only-key');at.button[0].click().run()
    assert not at.exception
    mk.assert_called_once_with('session-only-key')
    assert 'session-only-key' not in markdown(at)

def test_line_item_badges_cannot_reuse_a_prediction():
    import app
    row=dict(description='Support',quantity=1,unit_price=20,amount=20)
    rows=app.line_item_rows([row,row],[row])
    assert [r['Result'] for r in rows]==['Match','Missing']

def test_chart_counts_match_raw_csv():
    import app
    d=pd.read_csv(ROOT/'results/per_invoice.csv'); ids=app.shared_level4_ids(d,120)
    assert len(ids)==16
    counts=app.field_error_counts(d,ids)
    for r in counts.itertuples():
        field=next(k for k,v in app.FIELD_LABELS.items() if v==r.Field)
        assert r.Wrong==int((d[d.model.eq(r.Model)&d.id.isin(ids)]['f_'+field]<1).sum())
