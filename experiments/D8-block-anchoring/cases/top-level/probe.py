import markdown_it
md = markdown_it.MarkdownIt("commonmark")
cases = {
 "marker between items, col 0": "- one item\n<!-- #x -->\n- two item\n",
 "marker between items, indented 2": "- one item\n  <!-- #x -->\n- two item\n",
 "marker first in item": "- <!-- #x -->\n  one item\n- two item\n",
 "bullet char change": "- one\n- two\n* three\n",
 "tight list": "- a\n- b\n- c\n",
 "loose list (one blank)": "- a\n- b\n\n- c\n",
}
for k, s in cases.items():
    toks = [f"{t.type}@{t.level}" for t in md.parse(s) if t.nesting >= 0 and t.block]
    print(f"{k:34} top-level={sum(1 for t in md.parse(s) if t.level==0 and t.nesting==1 or (t.level==0 and t.nesting==0 and t.block))}  {' '.join(toks)}")
    if 'list' in k: print("   html:", md.render(s).replace("\n", ""))
