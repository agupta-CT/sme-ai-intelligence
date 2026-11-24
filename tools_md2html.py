import re, sys, html
src = open(sys.argv[1]).read()
try:
    import markdown
    body = markdown.markdown(src, extensions=['tables','fenced_code'])
    mode = "markdown-module"
except Exception:
    mode = "fallback"
    lines = src.split("\n"); out=[]; i=0; in_list=None; in_code=False
    def inline(t):
        t = html.escape(t, quote=False)
        t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?!\w)", r"<i>\1</i>", t)
        t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', t)
        return t
    def close_list():
        global in_list
        if in_list: out.append("</%s>" % in_list); in_list=None
    while i < len(lines):
        l = lines[i]
        if l.startswith("```"):
            if in_code: out.append("</pre>"); in_code=False
            else: close_list(); out.append('<pre style="background:#f4f4f4;padding:10px;border-radius:4px;font-size:12px;overflow-x:auto">'); in_code=True
            i+=1; continue
        if in_code: out.append(html.escape(l)); i+=1; continue
        if l.strip()=="---": close_list(); out.append("<hr>"); i+=1; continue
        m = re.match(r"^(#{1,4})\s+(.*)", l)
        if m: close_list(); n=len(m.group(1)); out.append("<h%d>%s</h%d>"%(n, inline(m.group(2)), n)); i+=1; continue
        if l.startswith("|") and i+1 < len(lines) and re.match(r"^\|[\s\-:|]+\|$", lines[i+1].strip()):
            close_list(); hdr=[c.strip() for c in l.strip().strip("|").split("|")]
            out.append('<table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse;font-size:13px"><tr>'+"".join("<th align=\"left\">%s</th>"%inline(c) for c in hdr)+"</tr>")
            i+=2
            while i < len(lines) and lines[i].startswith("|"):
                cells=[c.strip() for c in lines[i].strip().strip("|").split("|")]
                out.append("<tr>"+"".join("<td valign=\"top\">%s</td>"%inline(c) for c in cells)+"</tr>"); i+=1
            out.append("</table>"); continue
        m = re.match(r"^(\s*)[-*]\s+(.*)", l)
        if m:
            if in_list!="ul": close_list(); out.append("<ul>"); in_list="ul"
            out.append("<li>%s</li>"%inline(m.group(2))); i+=1; continue
        m = re.match(r"^(\s*)\d+\.\s+(.*)", l)
        if m:
            if in_list!="ol": close_list(); out.append("<ol>"); in_list="ol"
            out.append("<li>%s</li>"%inline(m.group(2))); i+=1; continue
        if l.strip()=="": close_list(); i+=1; continue
        close_list(); out.append("<p>%s</p>"%inline(l)); i+=1
    close_list(); body="\n".join(out)
doc = '<html><body style="font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.45;color:#222;max-width:900px">'+body+'</body></html>'
open(sys.argv[2],"w").write(doc)
print(mode, "html bytes:", len(doc))
