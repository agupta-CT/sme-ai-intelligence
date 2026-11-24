#!/usr/bin/env python3
"""Render a daily brief (markdown) as a readable HTML email + plain text + inline-image manifest.

usage: python3 tools_email.py daily_reports/YYYY-MM-DD.md --tracker AI_Research_Reading_Tracker.csv \
         --artifact https://claude.ai/artifact/XXXX --repo https://github.com/ORG/REPO --out daily_reports/YYYY-MM-DD.email.html
Writes: <out>, <out>.txt (plain-text alternative), <out>.manifest.json (ordered inline attachments: cid:att0 ...).
Charts are email-safe HTML tables. The architecture diagram (first fenced block in Section 5) is rendered to PNG with
headless Chrome when available; otherwise it stays as a styled <pre>. Every URL stays an active link.
"""
import re, sys, os, csv, json, html, argparse, subprocess, shutil, collections

C = {"ink":"#1a2230","muted":"#5b6676","line":"#d9dee6","bg":"#f6f7f9","card":"#ffffff","accent":"#1f5fbf","soft":"#e4ecf9",
     "p1":"#b3261e","p2":"#1f5fbf","p3":"#5b6676","pw":"#7a5aa6","ok":"#1e7f4f","warn":"#a3650a"}
FONT = "font-family:Arial,Helvetica,sans-serif;"

def ent(t): return "".join(c if ord(c) < 128 else "&#%d;" % ord(c) for c in t)
def esc(t): return html.escape(t or "", quote=False)
URL_RE = re.compile(r'(?<![\w"\'>/])((?:https?://)?(?:www\.)?(?:[a-z0-9-]+\.)+(?:com|ai|io|org|net|dev|co|google|edu|gov|cloud|sh|me)(?:/[^\s<>()\[\]"\']*[^\s<>()\[\]"\'.,;:])?)', re.I)
ARXIV_RE = re.compile(r'\barXiv[:\s]+(\d{4}\.\d{4,5})(v\d+)?', re.I)
AI_ID_RE = re.compile(r'\b(AI-\d{4})\b')

def inline(t, artifact):
    """escape, then markdown inline -> html, then autolink bare URLs, arXiv ids and tracker ids"""
    t = esc(t)
    holes = []
    def hold(s): holes.append(s); return "\x00%d\x00" % (len(holes) - 1)
    t = re.sub(r"`([^`]+)`", lambda m: hold('<code style="background:#eef1f5;padding:0 3px;border-radius:3px;font-size:92%%">%s</code>' % m.group(1)), t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", lambda m: hold('<a href="%s" style="color:%s">%s</a>' % (m.group(2), C["accent"], m.group(1))), t)
    t = ARXIV_RE.sub(lambda m: hold('<a href="https://arxiv.org/abs/%s" style="color:%s">arXiv %s%s</a>' % (m.group(1), C["accent"], m.group(1), m.group(2) or "")), t)
    def link_url(m):
        raw = m.group(1); href = raw if raw.lower().startswith("http") else "https://" + raw
        return hold('<a href="%s" style="color:%s;word-break:break-all">%s</a>' % (href, C["accent"], raw))
    t = URL_RE.sub(link_url, t)
    if artifact:
        t = AI_ID_RE.sub(lambda m: hold('<a href="%s#all" style="color:%s;text-decoration:none;border-bottom:1px dotted %s">%s</a>' % (artifact, C["accent"], C["accent"], m.group(1))), t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?!\w)", r"<i>\1</i>", t)
    t = re.sub(r"\x00(\d+)\x00", lambda m: holes[int(m.group(1))], t)
    return t

def md_blocks(md, artifact, pre_hook=None):
    lines = md.split("\n"); out = []; i = 0; lst = None; code = []; in_code = False; code_n = 0
    def close():
        nonlocal lst
        if lst: out.append("</%s>" % lst); lst = None
    while i < len(lines):
        l = lines[i]
        if l.startswith("```"):
            if in_code:
                in_code = False; body = "\n".join(code); code_n += 1
                rep = pre_hook(body, code_n) if pre_hook else None
                out.append(rep or '<pre style="background:#f1f3f6;border:1px solid %s;padding:10px;border-radius:6px;font-size:12px;line-height:1.35;overflow-x:auto;white-space:pre">%s</pre>' % (C["line"], esc(body)))
                code = []
            else: close(); in_code = True
            i += 1; continue
        if in_code: code.append(l); i += 1; continue
        if l.strip() == "---": close(); out.append('<hr style="border:0;border-top:1px solid %s;margin:22px 0">' % C["line"]); i += 1; continue
        m = re.match(r"^(#{1,4})\s+(.*)", l)
        if m:
            close(); n = len(m.group(1)); txt = inline(m.group(2), artifact)
            style = {1:"font-size:22px;margin:26px 0 8px", 2:"font-size:18px;margin:24px 0 8px;padding-top:8px;border-top:2px solid %s" % C["accent"], 3:"font-size:15px;margin:18px 0 6px", 4:"font-size:14px;margin:14px 0 4px;color:%s" % C["muted"]}[n]
            out.append('<h%d style="%s;color:%s;line-height:1.3">%s</h%d>' % (n, style, C["ink"] if n < 4 else C["muted"], txt, n)); i += 1; continue
        if l.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|$", lines[i+1].strip()):
            close(); hdr = [c.strip() for c in l.strip().strip("|").split("|")]
            rows = []; i += 2
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            t = '<table role="presentation" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-size:12.5px;width:100%%;margin:8px 0"><tr>' + "".join('<th align="left" style="background:%s;border:1px solid %s;color:%s">%s</th>' % (C["soft"], C["line"], C["ink"], inline(c, artifact)) for c in hdr) + "</tr>"
            for k, r in enumerate(rows):
                t += "<tr>" + "".join('<td valign="top" style="border:1px solid %s;background:%s">%s</td>' % (C["line"], "#ffffff" if k % 2 == 0 else "#fafbfc", inline(c, artifact)) for c in r) + "</tr>"
            out.append(t + "</table>"); continue
        m = re.match(r"^\s*[-*]\s+(.*)", l)
        if m:
            if lst != "ul": close(); out.append('<ul style="margin:6px 0 10px 20px;padding:0">'); lst = "ul"
            out.append('<li style="margin:3px 0">%s</li>' % inline(m.group(1), artifact)); i += 1; continue
        m = re.match(r"^\s*\d+\.\s+(.*)", l)
        if m:
            if lst != "ol": close(); out.append('<ol style="margin:6px 0 10px 22px;padding:0">'); lst = "ol"
            out.append('<li style="margin:3px 0">%s</li>' % inline(m.group(1), artifact)); i += 1; continue
        if l.strip() == "": close(); i += 1; continue
        close(); out.append('<p style="margin:6px 0">%s</p>' % inline(l, artifact)); i += 1
    close(); return "\n".join(out)

def bar_chart(title, rows, color_fn, unit=""):
    """rows: [(label, value)] -> email-safe horizontal bars"""
    mx = max([v for _, v in rows] + [1])
    t = '<div style="margin:14px 0"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:%s;margin-bottom:6px">%s</div><table role="presentation" cellpadding="0" cellspacing="0" style="border-collapse:collapse;width:100%%;font-size:12.5px">' % (C["muted"], esc(title))
    for label, v in rows:
        w = int(round(100 * v / mx)) if mx else 0
        t += ('<tr><td style="padding:3px 8px 3px 0;white-space:nowrap;width:34%%;color:%s">%s</td>'
              '<td style="padding:3px 0"><table role="presentation" cellpadding="0" cellspacing="0" style="border-collapse:collapse;width:100%%"><tr>'
              '<td style="width:%d%%;background:%s;height:12px;border-radius:3px"></td><td style="padding-left:6px;font-size:12px;color:%s;white-space:nowrap">%s%s</td></tr></table></td></tr>'
              % (C["ink"], esc(label), max(w, 1), color_fn(label), C["muted"], v, unit))
    return t + "</table></div>"

def render_png(pre_text, out_png):
    chrome = next((p for p in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser")] if p and os.path.exists(p)), None)
    if not chrome: return False
    page = ('<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#ffffff}pre{margin:0;padding:18px 22px;font:13px/1.45 "SF Mono",Menlo,Consolas,monospace;color:#1a2230;background:#f6f7f9;border:1px solid #d9dee6;border-radius:8px;display:inline-block}</style></head><body><pre>%s</pre></body></html>' % esc(pre_text))
    tmp = out_png + ".html"; open(tmp, "w").write(page)
    try:
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1000,420", "--force-device-scale-factor=2", "--screenshot=" + out_png, "file://" + os.path.abspath(tmp)], check=True, capture_output=True, timeout=60)
    except Exception:
        return False
    finally:
        try: os.remove(tmp)
        except OSError: pass
    try:
        from PIL import Image
        im = Image.open(out_png).convert("RGB"); bbox = Image.eval(im, lambda p: 255 - p).getbbox()
        if bbox: im.crop((max(0, bbox[0]-8), max(0, bbox[1]-8), min(im.width, bbox[2]+8), min(im.height, bbox[3]+8))).save(out_png)
    except Exception: pass
    return os.path.exists(out_png)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("md"); ap.add_argument("--tracker", default="AI_Research_Reading_Tracker.csv"); ap.add_argument("--artifact", default=""); ap.add_argument("--repo", default=""); ap.add_argument("--out", required=True)
    a = ap.parse_args(); md = open(a.md, encoding="utf-8").read(); date = re.search(r"\d{4}-\d{2}-\d{2}", os.path.basename(a.md)).group(0)
    rows = list(csv.DictReader(open(a.tracker, newline="", encoding="utf-8"))) if os.path.exists(a.tracker) else []
    new = [r for r in rows if r["discovered_date"] == date]; pend = [r for r in rows if r["status"] in ("Not Started", "In Progress")]
    # header facts from the brief
    hdr = {k: v for k, v in re.findall(r"^\*\*([^*]+):\*\*\s*(.*)$", md, re.M)}
    # five things
    sec1 = re.search(r"## Section 1[^\n]*\n(.*?)\n---", md, re.S); five = []
    if sec1:
        for m in re.finditer(r"^### (\d+)\.\s+(.*?)\n(.*?)(?=^### \d+\.|\Z)", sec1.group(1), re.S | re.M):
            bullets = re.findall(r"^- \*\*([^*]+):\*\*\s*(.*)$", m.group(3), re.M)
            five.append((m.group(2).strip(), bullets))
    # body = everything from Section 2 on
    body_md = md[md.find("## Section 2"):] if "## Section 2" in md else md
    manifest = []; img_dir = os.path.splitext(a.out)[0] + "_img"; os.makedirs(img_dir, exist_ok=True)
    def pre_hook(body, n):
        if "COMPACT" in body or "──" in body or "►" in body:  # the architecture diagram
            png = os.path.join(img_dir, "diagram%d.png" % n)
            if render_png(body, png):
                manifest.append({"path": os.path.abspath(png), "filename": os.path.basename(png), "mimeType": "image/png", "inline": True})
                return '<div style="margin:10px 0"><img src="cid:att%d" alt="Reference design diagram" style="max-width:100%%;height:auto;border:1px solid %s;border-radius:8px"></div><div style="font-size:11px;color:%s">Diagram rendered from the brief; the text version is in the attached markdown.</div>' % (len(manifest) - 1, C["line"], C["muted"])
        return None
    body_html = md_blocks(body_md, a.artifact, pre_hook)
    # charts from tracker
    prio = collections.Counter(r["priority"] for r in new) or collections.Counter(r["priority"] for r in rows)
    pcolor = {"P1": C["p1"], "P2": C["p2"], "P3": C["p3"], "Watchlist": C["pw"]}
    chart1 = bar_chart("Items recorded this run, by priority" if new else "Tracker by priority", [(p, prio.get(p, 0)) for p in ["P1", "P2", "P3", "Watchlist"]], lambda l: pcolor.get(l, C["accent"]))
    topic_min = collections.Counter()
    for r in pend:
        if r["priority"] in ("P1", "P2"):
            for t in r["topics"].split(";")[:2]:
                if t: topic_min[t] += int(r["est_read_min"] or 0)
    top = topic_min.most_common(7)
    chart2 = bar_chart("Essential backlog (P1 + P2) by topic, minutes", [(t, v) for t, v in top], lambda l: C["accent"]) if top else ""
    p1h = round(sum(int(r["est_read_min"] or 0) for r in pend if r["priority"] == "P1") / 60, 1)
    # assemble
    five_html = ""
    for n, (title, bullets) in enumerate(five, 1):
        five_html += ('<table role="presentation" cellpadding="0" cellspacing="0" style="border-collapse:collapse;width:100%%;margin:10px 0"><tr>'
                      '<td valign="top" style="width:38px;padding:12px 0 0 12px;font-size:22px;font-weight:bold;color:%s">%d</td>'
                      '<td style="padding:12px 14px 12px 6px;background:%s;border:1px solid %s;border-radius:8px">'
                      '<div style="font-size:15px;font-weight:bold;color:%s;margin-bottom:6px">%s</div>' % (C["accent"], n, C["card"], C["line"], C["ink"], inline(title, a.artifact)))
        for k, v in bullets:
            five_html += '<div style="margin:4px 0;font-size:13.5px"><span style="color:%s;font-weight:bold">%s.</span> %s</div>' % (C["muted"], esc(k), inline(v, a.artifact))
        five_html += "</td></tr></table>"
    links = []
    if a.artifact: links.append('<a href="%s" style="display:inline-block;background:%s;color:#ffffff;text-decoration:none;padding:8px 14px;border-radius:6px;font-weight:bold;margin:4px 6px 4px 0">Open the reading tracker</a>' % (a.artifact, C["accent"]))
    if a.repo: links.append('<a href="%s/blob/main/daily_reports/%s.md" style="display:inline-block;background:%s;color:%s;text-decoration:none;padding:8px 14px;border-radius:6px;font-weight:bold;margin:4px 6px 4px 0">Brief in the repo</a>' % (a.repo, date, C["soft"], C["accent"]))
    facts = "".join('<td style="padding:6px 14px 6px 0;font-size:12px;color:%s">%s<br><span style="font-size:18px;font-weight:bold;color:%s">%s</span></td>' % (C["muted"], esc(k), C["ink"], esc(v)) for k, v in [
        ("Items reviewed", re.sub(r"\s*\(.*", "", hdr.get("Number of items reviewed", "")).split(" across")[0] or "n/a"), ("New items", (hdr.get("New items selected", "").split(" ")[0] or "n/a")), ("P1 reading left", "%s h" % p1h), ("Pending", str(len(pend)))])
    doc = ('<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Daily AI Digest (SME Edition) - %s</title></head>'
           '<body style="margin:0;background:%s;%scolor:%s;font-size:14px;line-height:1.5">'
           '<table role="presentation" cellpadding="0" cellspacing="0" style="width:100%%;border-collapse:collapse"><tr><td align="center" style="padding:16px">'
           '<table role="presentation" cellpadding="0" cellspacing="0" style="max-width:860px;width:100%%;border-collapse:collapse">'
           '<tr><td style="background:%s;color:#ffffff;padding:22px 24px;border-radius:10px 10px 0 0">'
           '<div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;opacity:.85">Daily AI Digest &middot; SME Edition</div>'
           '<div style="font-size:24px;font-weight:bold;margin-top:4px">Applied AI Daily Intelligence Brief</div>'
           '<div style="font-size:13px;margin-top:6px;opacity:.9">%s &middot; window %s</div></td></tr>'
           '<tr><td style="background:%s;padding:16px 24px;border:1px solid %s;border-top:0">'
           '<table role="presentation" cellpadding="0" cellspacing="0"><tr>%s</tr></table><div style="margin-top:10px">%s</div></td></tr>'
           '<tr><td style="background:%s;padding:18px 24px;border:1px solid %s;border-top:0;border-radius:0 0 10px 10px">'
           '<h2 style="font-size:18px;margin:4px 0 6px;color:%s">The five things to know today</h2>%s'
           '<table role="presentation" cellpadding="0" cellspacing="0" style="width:100%%"><tr><td valign="top" style="width:50%%;padding-right:10px">%s</td><td valign="top" style="width:50%%">%s</td></tr></table>'
           '%s'
           '<hr style="border:0;border-top:1px solid %s;margin:24px 0 12px"><div style="font-size:12px;color:%s">Update reading status by clicking in the tracker, or reply in Claude with <code>READ AI-xxxx</code>, <code>START</code>, <code>SKIP</code>, <code>DEEP DIVE</code>, <code>EXPLAIN</code>, <code>COMPARE</code>, <code>IMPLEMENT</code>. Benchmarks are vendor-reported unless marked independent. Generated by the SME intelligence routine.</div>'
           '</td></tr></table></td></tr></table></body></html>'
           % (date, C["bg"], FONT, C["ink"], C["ink"], esc(hdr.get("Date", date)), esc(hdr.get("Research window", "")), C["card"], C["line"], facts, "".join(links), C["card"], C["line"], C["ink"], five_html, chart1, chart2, body_html, C["line"], C["muted"]))
    open(a.out, "w", encoding="utf-8").write(ent(doc))
    txt = re.sub(r"\n{3,}", "\n\n", md)
    open(a.out + ".txt", "w", encoding="utf-8").write(txt)
    json.dump(manifest, open(a.out + ".manifest.json", "w"), indent=1)
    print("email html:", a.out, len(doc), "bytes; inline images:", len(manifest))

if __name__ == "__main__": main()
