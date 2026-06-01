import json, re, sys, html

VIP = {"opm@hbs.edu","rvlabrador@revlv.com","board@revlv.com"}

def strip_html(s):
    if not s: return ""
    # remove style/script blocks
    s = re.sub(r'(?is)<style.*?</style>', ' ', s)
    s = re.sub(r'(?is)<script.*?</script>', ' ', s)
    s = re.sub(r'(?is)<!--.*?-->', ' ', s)
    # block-level -> newline
    s = re.sub(r'(?i)<br\s*/?>', '\n', s)
    s = re.sub(r'(?i)</(p|div|tr|table|h[1-6]|li|blockquote)>', '\n', s)
    s = re.sub(r'(?i)<(p|div|tr|h[1-6]|li)[^>]*>', '\n', s)
    s = re.sub(r'(?s)<[^>]+>', ' ', s)
    s = html.unescape(s)
    return s

def clean_text(s):
    if not s: return ""
    # if it looks like it still has html/css, strip
    if re.search(r'<[a-zA-Z/!]', s) or '@media' in s or 'font-family' in s:
        s = strip_html(s)
    s = html.unescape(s)
    # remove zero-width/invisible chars
    s = re.sub(r'[​‌‍­͏؜ᅟᅠ឴឵᠎⁠﻿‎‏]', '', s)
    s = s.replace(' ',' ')
    # normalize line endings
    s = s.replace('\r\n','\n').replace('\r','\n')
    # collapse 3+ newlines
    s = re.sub(r'[ \t]+\n', '\n', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    # collapse runs of spaces
    s = re.sub(r'[ \t]{2,}', ' ', s)
    return s.strip()

def pick_email(sender):
    if not sender: return ""
    m = re.search(r'<([^>]+)>', sender)
    email = m.group(1) if m else sender
    return email.strip().strip('"').lower()

def pick_name(sender, email):
    if not sender: return email.split('@')[0]
    m = re.match(r'\s*"?([^"<]+?)"?\s*<', sender)
    if m and m.group(1).strip():
        return m.group(1).strip()
    return email.split('@')[0]

def process(thread):
    msgs = thread.get('messages',[])
    if not msgs:
        return None
    latest = msgs[-1]
    sender_raw = latest.get('sender','')
    email = pick_email(sender_raw)
    name = pick_name(sender_raw, email)
    plain = latest.get('plaintextBody') or ''
    body = clean_text(plain)
    # if body still empty or looks like css/html residue, use htmlBody
    if (not body) or len(body) < 3 or ('@media' in body) or body.startswith('<style'):
        bodyh = clean_text(strip_html(latest.get('htmlBody') or ''))
        if bodyh and len(bodyh) > len(body):
            body = bodyh
    fallback = False
    if not body:
        body = clean_text(latest.get('snippet','') or '')
        fallback = True
    labels = latest.get('labelIds',[]) or []
    obj = {
        "id": thread.get('id'),
        "sender": email,
        "senderName": name,
        "date": latest.get('date'),
        "subject": latest.get('subject',''),
        "snippet": latest.get('snippet',''),
        "body": body,
        "labels": labels,
        "isUnread": "UNREAD" in labels,
        "isImportant": "IMPORTANT" in labels,
        "isVip": email in VIP
    }
    return obj, fallback

if __name__ == '__main__':
    raw = json.load(open(sys.argv[1]))
    obj, fb = process(raw)
    out = sys.argv[2]
    json.dump(obj, open(out,'w'), ensure_ascii=False, indent=2)
    print("FALLBACK" if fb else "ok", obj['id'], "| latest sender:", obj['sender'], "| unread:", obj['isUnread'])
