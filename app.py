"""LDS Document Extraction Arena. Local replay is the default; live calls are explicit."""
import base64
import html
import json
import os
import sys
import tempfile
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'runner'))
import run_models
import score
from runner.validation import load_json, validate_invoice, validate_image
from learner.matching import match_rows
from learner.report import summarize

load_dotenv(ROOT / '.env', override=False)
DATA, RESULTS = ROOT / 'data/synthetic', ROOT / 'results'
SMALL, BIG = 'gemini-3.1-flash-lite', 'gemini-3.6-flash'
MODELS = [SMALL, BIG, 'gemini-3.8-flash']
NAMES = {SMALL: 'Gemini 3.1 Flash-Lite', BIG: 'Gemini 3.6 Flash', MODELS[2]: 'Gemini 3.8 Flash'}
REPO_URL = 'https://github.com/devsutharsystems/document-extraction-arena'
FIELD_LABELS = {'invoice_number':'Invoice number', 'vendor':'Vendor', 'invoice_date':'Date', 'currency':'Currency', 'subtotal':'Subtotal', 'tax':'Tax', 'total':'Total', 'line_items':'Line items'}
IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg'}
CSS = '''<style>
:root{color-scheme:light}
#MainMenu,footer,[data-testid="stDecoration"],[data-testid="stToolbar"]{display:none}
[data-testid="stHeader"]{background:transparent;height:0}
.block-container{max-width:1320px;padding:1.1rem 2.5rem 3rem}
[data-testid="stVerticalBlock"]{gap:.65rem}
[data-testid="stAppViewContainer"],.stApp{background:#fff;color:#181818}
.brand{display:flex;align-items:center;gap:12px;padding-bottom:12px;border-bottom:1px solid #e6e6e6;margin-bottom:12px}
.brand img{width:34px;height:34px}.brand strong{font-size:20px;letter-spacing:-.5px}.brand small{display:block;color:#707070;font-size:12px;margin-top:2px}
.brand .local{margin-left:auto;font-size:12px;color:#707070}
h1.hero{font-size:34px;line-height:1.12;letter-spacing:-1.3px;margin:0 0 10px;padding:0;font-weight:750}
p.sub{color:#656565;font-size:17px;max-width:760px;margin:0 0 12px;line-height:1.6}
[data-baseweb="tab-list"]{gap:28px;margin-bottom:4px}[data-baseweb="tab"]{font-weight:600;font-size:15px;padding:0 0 12px}
[data-baseweb="tab-highlight"]{background:#181818;height:2px}
[data-testid="stImage"]{background:#f7f7f5;padding:12px}[data-testid="stImage"] img{max-height:530px;object-fit:contain;width:100%}
.source-note{font-size:12px;color:#737373;margin:0 0 4px}.source-note b{color:#247051}
.verdict{display:flex;align-items:baseline;gap:9px;margin:6px 0 4px}.verdict strong{font-size:29px;letter-spacing:-1px}.verdict span{font-size:14px;color:#626262}
.evidence{width:100%;border-collapse:collapse;font-size:14px;table-layout:fixed}.evidence th,.evidence td{border:0}.evidence th{text-align:left;font-size:11px;color:#767676;font-weight:500;padding:11px 8px;border-bottom:1px solid #ddd}.evidence td{padding:12px 8px;border-bottom:1px solid #eee;word-break:break-word;vertical-align:top}.evidence tr.mismatch{background:#fcf4f3}.evidence td:first-child{font-weight:600;width:22%}.match{color:#267157}.mismatch-mark{color:#b43d48}.state{font-size:11px;font-weight:600;white-space:nowrap}.field-heading{font-size:17px;font-weight:650;margin:5px 0 8px}.small-note{font-size:12px;line-height:1.5;color:#666;margin:12px 0}
.compare{padding:20px 0;border-top:2px solid #181818}.compare .model{font-size:15px;font-weight:600}.compare .exact{font-size:42px;letter-spacing:-2px;line-height:1.3}.compare .exact span{font-size:17px;letter-spacing:0;color:#777}.compare .stats{font-size:13px;color:#666;line-height:1.9}
[data-testid="stBaseButton-primary"],button[kind="primary"]{background:#000;color:#ffcf25;border-color:#000}
.foot{border-top:1px solid #e6e6e6;margin-top:30px;padding-top:16px;font-size:12px;color:#777}
@media(max-width:700px){.block-container{padding:1.2rem 1rem 2rem}.brand strong{font-size:17px}.brand .local{display:none}h1.hero{font-size:30px}.sub{font-size:15px}.evidence{font-size:12px}.evidence th,.evidence td{padding:9px 5px}[data-testid="stImage"] img{max-height:470px}[data-baseweb="tab-list"]{gap:17px}}
</style>'''


def esc(value):
    return html.escape('—' if value is None else str(value))


def display(value):
    if isinstance(value, (float, int)) and not isinstance(value, bool):
        return f'{value:,.2f}'
    return '—' if value is None else str(value)


def header():
    st.markdown(CSS, unsafe_allow_html=True)
    logo = base64.b64encode((ROOT/'assets/lds-logo.svg').read_bytes()).decode()
    st.markdown(f'<div class="brand"><img src="data:image/svg+xml;base64,{logo}" alt="LDS"/><div><strong>Document Extraction Arena</strong><small>By Dev Suthar · An LDS project</small></div><span class="local">Your local workbench</span></div><h1 class="hero">Read the invoice. Check the evidence.</h1><p class="sub">See what the model read, compare it with the answer key, and follow every mismatch back to the source.</p>', unsafe_allow_html=True)


def evaluate(truth, pred):
    if truth is None:
        return {f:'na' for f in FIELD_LABELS}, None
    values, _ = score.score_invoice(truth, pred)
    report = summarize(values)
    return {f:('ok' if v == 1 else 'bad') for f,v in values.items()}, report['correct']


def line_item_rows(truth_items, pred_items):
    predictions = pred_items if isinstance(pred_items, list) else []
    pairs = match_rows(truth_items, predictions) if truth_items is not None else []
    matched_predictions = {j for _, j in pairs}
    rows = [{'Result':('Unscored' if truth_items is None else 'Match' if j in matched_predictions else 'Review'),
             'Description':p.get('description'), 'Qty':p.get('quantity'), 'Unit price':p.get('unit_price'), 'Amount':p.get('amount')}
            for j,p in enumerate(predictions) if isinstance(p,dict)]
    for i,p in enumerate(truth_items or []):
        if i not in {a for a,_ in pairs}:
            rows.append({'Result':'Missing', 'Description':p['description'], 'Qty':p['quantity'], 'Unit price':p['unit_price'], 'Amount':p['amount']})
    return rows


def render_fields(truth, pred, status, n_correct, *, differences=False):
    st.markdown(f'<div class="verdict"><strong>{n_correct} of 8</strong><span>fields match the answer key</span></div>' if n_correct is not None else '<div class="verdict"><strong>Extracted fields</strong></div>', unsafe_allow_html=True)
    if n_correct is not None:
        st.caption('Every field matches.' if n_correct == 8 else f'{8-n_correct} field{"s" if 8-n_correct!=1 else ""} to review. A high average can still hide an important mistake.')
    else:
        st.caption('No answer key supplied. Extracted values are not verified.')
    rows=[]
    for field,label in FIELD_LABELS.items():
        if field=='line_items' or (differences and status[field]=='ok'):
            continue
        got=pred.get(field)
        wanted=truth.get(field) if truth else None
        state=status[field]
        rows.append(f'<tr class="{"mismatch" if state=="bad" else ""}"><td>{label}</td><td>{esc(display(got))}</td><td>{esc(display(wanted))}</td><td class="state {"match" if state=="ok" else "mismatch-mark" if state=="bad" else ""}">{"✓ Match" if state=="ok" else "≠ Review" if state=="bad" else "Unscored"}</td></tr>')
    st.markdown('<table class="evidence"><thead><tr><th>Field</th><th>Model read</th><th>Answer key</th><th>Check</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table>',unsafe_allow_html=True)
    if differences and n_correct==8:
        st.success('No mismatches in this saved response.')
    items=line_item_rows(truth.get('line_items') if truth else None,pred.get('line_items'))
    with st.expander(f'Line items · {len(pred.get("line_items") or [])} returned · {"match" if status["line_items"]=="ok" else "review" if truth else "unscored"}'):
        st.caption('Rows are matched one to one. Repeated descriptions are allowed; a returned row cannot earn credit twice.')
        if items:
            st.dataframe(pd.DataFrame(items),hide_index=True,width='stretch')
        else:
            st.write('Both lists are empty.' if truth and not truth['line_items'] else 'No line items returned.')


def render_evidence(image, name, truth, pred, *, key):
    if pred is None:
        st.warning('This response does not contain valid invoice JSON. Open the raw evidence to inspect it.')
        return
    try:
        validate_invoice(pred, partial=True)
        status, correct=evaluate(truth,pred)
    except (ValueError, TypeError) as exc:
        st.warning(f'Cannot score this invoice: {exc}')
        return
    left,right=st.columns([.95,1.15],gap='large')
    with left:
        st.markdown('<div class="field-heading">The source invoice</div>',unsafe_allow_html=True)
        st.image(image,caption=f'{name} · Synthetic invoice. Use the image expand control for detail.',width='stretch')
    with right:
        focus=st.radio('Show', ['All fields','Differences only'],horizontal=True,key=f'{key}_filter')
        render_fields(truth,pred,status,correct,differences=focus=='Differences only')
        with st.expander('Raw evidence & report'):
            st.json(pred,expanded=1)
            payload={'invoice':name,'predicted':pred,'answer_key':truth,'field_status':status,'fully_correct':correct==8 if correct is not None else None,'method':'LDS deterministic scorer 1.0.0','scope':'Synthetic teaching example; not a real-document accuracy claim.'}
            st.download_button('Download this report',json.dumps(payload,indent=2,allow_nan=False),file_name='invoice-review.json',mime='application/json',key=f'{key}_download')


def saved_runs():
    st.markdown('<div class="source-note"><b>Saved responses</b> · Inspect the original measured run. No API key or new request.</div>',unsafe_allow_html=True)
    keys=sorted(DATA.glob('*/*.json'))
    selected={p.stem:p for p in keys}
    if not selected:
        st.info('Generate the teaching dataset with python generator/generate_invoices.py.');return
    ids=list(selected)
    c1,c2=st.columns([1.2,1])
    inv=c1.selectbox('Invoice',ids,index=ids.index('level4_hard_014') if 'level4_hard_014' in ids else 0,key='saved_invoice')
    available=[m for m in MODELS if (RESULTS/'raw'/m/f'{inv}.json').exists() and json.loads((RESULTS/'raw'/m/f'{inv}.json').read_text()).get('error') is None]
    if not available:
        st.info('There is no saved successful response for this invoice.');return
    model=c2.selectbox('Model',available,format_func=lambda x:NAMES.get(x,x),key='saved_model')
    truth=validate_invoice(load_json(selected[inv].read_bytes()))
    record=json.loads((RESULTS/'raw'/model/f'{inv}.json').read_text())
    image=next((p for p in selected[inv].parent.glob(inv+'.*') if p.suffix in IMAGE_SUFFIXES),None)
    if image is None:
        st.warning('The original image is missing. Restore the reference archive before comparing it.');return
    render_evidence(str(image),inv,truth,score.parse_response(record['response_text']),key='saved')
    if inv.startswith('level4') or inv=='level2_mixed_003':
        st.caption('Historical benchmark: numeric dates follow the generated vendor locale. The original prompt did not specify that policy. Inspect ambiguity before calling a mismatch a model failure.')


def friendly_error(err):
    value=str(err)
    if '429' in value or 'RESOURCE_EXHAUSTED' in value:
        return 'Google rejected the request because of a rate or quota limit. Check your project limits in AI Studio before retrying. No automatic retry was made.'
    if '503' in value or 'UNAVAILABLE' in value:
        return 'Google is busy. Your input is still here; try once later. No automatic retry was made.'
    if any(x in value for x in ('API key','401','403','API_KEY','AUTH')):
        return 'Google did not accept this key or model access. Check your Google project and model permissions.'
    return 'The extraction did not finish. Check your connection and model access. No automatic retry was made.'


def run_once(model,image_bytes,suffix,api_key):
    suffix=validate_image(image_bytes)
    with tempfile.TemporaryDirectory() as tmp:
        file=Path(tmp)/('invoice'+suffix);file.write_bytes(image_bytes)
        return run_models.extract(model,file,no_retry=True,client=run_models.make_client(api_key))


def tab_try():
    st.write('Make one new extraction with your own Gemini key. Saved runs work without one.')
    source=st.radio('Invoice source',['Synthetic sample','Upload an image'],horizontal=True,key='source')
    data=truth=name=None;invalid=False
    if source=='Synthetic sample':
        samples=sorted((ROOT/'examples/samples').glob('sample_*.json'))
        choice=st.selectbox('Sample',[p.stem for p in samples],format_func=lambda x:{'sample_01':'US software invoice (USD)','sample_02':'UK print shop (GBP)','sample_03':'Indian GST bill (INR)'}.get(x,x),key='sample')
        file=next((p for p in (ROOT/'examples/samples').glob(choice+'.*') if p.suffix in IMAGE_SUFFIXES),None)
        if file:
            data=file.read_bytes();name=choice;truth=validate_invoice(load_json(file.with_suffix('.json').read_bytes()))
    else:
        st.caption('The local server holds the file in memory and sends it to Google only when you click Extract once. Use synthetic documents. Free-tier Google inputs may be used to improve its products.')
        upload=st.file_uploader('Invoice image',type=['png','jpg','jpeg'],max_upload_size=10)
        answer=st.file_uploader('Answer key (optional)',type=['json'],max_upload_size=1)
        if upload:data=upload.getvalue();name=upload.name
        if answer:
            try:truth=validate_invoice(load_json(answer.getvalue()))
            except ValueError as exc:st.error(str(exc));invalid=True
    if data:
        try:suffix=validate_image(data)
        except ValueError as exc:st.error(str(exc));invalid=True
        if not invalid:
            with st.expander('Preview the input invoice',expanded=False):st.image(data,width='stretch')
    model=st.selectbox('Gemini model',MODELS,format_func=lambda x:NAMES[x],key='live_model')
    env=os.environ.get('GEMINI_API_KEY','')
    typed=st.text_input('Your Gemini API key',type='password',key='api_key_input',disabled=bool(env),placeholder='Using your local .env key' if env else 'Paste your key for this session')
    st.caption('Your key is never written by the app. A new extraction sends this image to Google. Billing depends on your Google project; free quota is not guaranteed. One click makes at most one request.')
    st.markdown('[API keys](https://aistudio.google.com/apikey) · [Pricing](https://ai.google.dev/gemini-api/docs/pricing) · [Data terms](https://ai.google.dev/gemini-api/terms)')
    if st.button('Extract once',type='primary',disabled=not data or invalid):
        if not (env or typed):st.info('Add your Gemini API key first. No request was made.')
        else:
            with st.spinner('Reading the invoice. One request, no automatic retries…'):
                try:result=run_once(model,data,suffix,env or typed)
                except Exception:result={'error':'REQUEST_FAILED'}
            st.session_state.result={'res':result,'truth':truth,'image':data,'name':name,'model':model}
    out=st.session_state.get('result')
    if not out:return
    res=out['res']
    if res.get('error'):st.error(friendly_error(res['error']));return
    pred=score.parse_response(res.get('response_text'))
    if pred is None:st.warning('The response did not match the invoice schema. No score was awarded. Review your input before making another request.');return
    st.divider();st.caption(f'Result for {out["name"]} · {NAMES.get(out["model"],out["model"])}')
    render_evidence(out['image'],out['name'],out['truth'],pred,key='live')
    price=score.PRICES.get(out['model'])
    if price:
        cost=(res.get('input_tokens',0)*price[0]+(res.get('output_tokens',0)+res.get('thinking_tokens',0))*price[1])/1e6
        st.caption(f'Request duration: {res.get("seconds",0):.2f} s · Estimated paid-tier equivalent: ${cost:.5f}. Actual charges depend on your account. Price snapshot: 8 October 2026; check current pricing.')


def shared_level4_ids(per_invoice,n):
    ok=per_invoice[(per_invoice.level=='level4_hard') & ~per_invoice.api_error]
    return sorted(set(ok[ok.model==BIG].id)&set(ok[ok.model==SMALL].id))[:n]


def field_error_counts(per_inv,ids):
    rows=[]
    for model in (SMALL,BIG):
        sub=per_inv[per_inv.id.isin(ids)&(per_inv.model==model)&~per_inv.api_error]
        for field,label in FIELD_LABELS.items():rows.append({'Field':label,'Model':model,'Wrong':int((sub['f_'+field]<1).sum())})
    return pd.DataFrame(rows)


def error_chart(counts,n):
    enc=dict(y=alt.Y('Field:N',sort=list(FIELD_LABELS.values()),title=None),yOffset=alt.YOffset('Model:N',sort=[SMALL,BIG]))
    x=alt.X('Wrong:Q',title=f'Invoices with a mismatch (out of {n})',scale=alt.Scale(domain=[0,int(counts.Wrong.max())+1]),axis=alt.Axis(tickMinStep=1,format='d'))
    bars=alt.Chart(counts).mark_bar(size=13).encode(x=x,color=alt.Color('Model:N',scale=alt.Scale(domain=[SMALL,BIG],range=['#272727','#b58b24']),legend=alt.Legend(orient='top',title=None)),**enc)
    labels=alt.Chart(counts).transform_filter(alt.datum.Wrong>0).mark_text(align='left',dx=4).encode(x='Wrong:Q',text=alt.Text('Wrong:Q',format='d'),**enc)
    return (bars+labels).properties(height=300,background='transparent').configure_view(strokeWidth=0)


def tab_results():
    per=pd.read_csv(RESULTS/'per_invoice.csv');ids=shared_level4_ids(per,120)
    st.subheader('Same invoices. A clearer comparison.')
    st.caption(f'Historical measurements · {len(ids)} shared hard invoices · Synthetic, one layout · Preliminary')
    cols=st.columns(2)
    for col,model in zip(cols,[SMALL,BIG]):
        sub=per[per.model.eq(model)&per.id.isin(ids)&~per.api_error]
        with col:
            exact=int(sub.exact.sum())
            st.markdown(f'<div class="compare"><div class="model">{NAMES[model]}</div><div class="exact">{exact}<span> / {len(ids)} fully correct</span></div><div class="stats">Mean field score {sub.accuracy.mean()*100:.1f}%<br>{sub.seconds.mean():.2f} seconds per successful call<br>${sub.cost_usd.mean():.5f} estimated paid-tier cost per invoice</div></div>',unsafe_allow_html=True)
    st.caption('Same invoices for both models. This is a saved exploratory run, not a production accuracy ranking. Dollar values are estimates; these original runs used free quota. Retry time is excluded.')
    st.markdown('#### Where did the fields differ?')
    st.altair_chart(error_chart(field_error_counts(per,ids),len(ids)),width='stretch')
    with st.expander('Dataset coverage and limits'):
        st.write('120 generated invoices, 30 per level. Flash-Lite answered all 120; Flash 3.6 answered the first 16 hard invoices. Both saw the same image for each paired comparison. Unanswered API requests are excluded from extraction scores and kept in a separate error log.')
        st.warning('Hard-set dates can be ambiguous and some digits are degraded. The answer key is what the generator intended, not proof that a human could read it. Review these cases before drawing a model-quality conclusion.')
        st.dataframe(pd.read_csv(RESULTS/'summary.csv'),hide_index=True,width='stretch')
    st.download_button('Download paired results',pd.read_csv(RESULTS/'summary_same_invoices.csv').query("level == 'level4_hard'").to_csv(index=False),'paired-results.csv','text/csv')


def tab_how():
    st.subheader('An answer key is only the beginning.')
    st.markdown('''**1. Generate a document.** Python chooses fictional invoice values, then renders an image. The matching JSON records those values before a model sees the image.

**2. Ask for structured fields.** Gemini sees the image, not the answer key. The current prompt requests JSON and states a date policy. Original saved runs preserve the older prompt, which did not specify that policy.

**3. Validate, then compare.** Reject invalid numbers and malformed rows. Compare seven scalar fields and the line-item collection. A returned row can match only one expected row, even when descriptions repeat. Money matches within strictly less than 0.005 of the key.

**4. Keep two measures.** The mean field score tells you how much matched. A fully correct invoice requires all eight fields to match. A wrong invoice number can matter even when every amount is right.

**5. Audit the evidence.** An ambiguous image is a dataset limitation. A provider error is not an extraction error. Record them separately and compare models on the same documents.''')
    st.info('This is a teaching benchmark using synthetic invoices and one layout. It does not establish accuracy on real invoices, other languages, handwriting or unseen layouts.')
    st.markdown('#### Your three build tasks')
    st.code('learner/normalize.py  →  finite decimal values\nlearner/matching.py   →  one-to-one row matching\nlearner/report.py     →  exact versus average scores',language='text')
    st.write('Run python -m pytest tests/test_learning.py -q after each task. Recovery checkpoints preserve your previous work in .backups/.')
    st.markdown(f'[Original project by Dev Suthar]({REPO_URL}) · Apache 2.0. This local LDS edition preserves the original data and measurements.')


def main():
    st.set_page_config(page_title='Document Extraction Arena · LDS',layout='wide',initial_sidebar_state='collapsed')
    header()
    if (ROOT/'STARTER').exists():st.info('Build-along starter: finish the three files in learner/. Run the focused tests after each step, or restore a named checkpoint to continue.')
    tabs=st.tabs(['Review an invoice','Compare models','How it works'],key='view',on_change='rerun')
    try:
        with tabs[0]:
            if tabs[0].open:
                mode=st.radio('Choose a workflow',['Saved run','New extraction'],horizontal=True,key='workflow',label_visibility='collapsed')
                if mode=='Saved run':saved_runs()
                else:tab_try()
        with tabs[1]:
            if tabs[1].open:tab_results()
        with tabs[2]:
            if tabs[2].open:tab_how()
    except NotImplementedError:
        st.info('This learner function is waiting for you. Follow the guide or run python scripts/restore.py with its name to restore a checkpoint.')
    st.markdown('<div class="foot">Fictional invoices. Measured responses. Checks you can inspect. · Local LDS edition 1.0</div>',unsafe_allow_html=True)

if __name__=='__main__':main()
