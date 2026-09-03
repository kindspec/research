#!/usr/bin/env python3
"""Write a .tbl out as a real .xlsx containing a real Excel Table (ListObject)
whose computed columns carry LIVE structured-reference formulas.

Hand-written OOXML; no library. Named .tbl columns map 1:1 onto structured
references, which is the whole point: `total = qty * unit` becomes
`Orders[[#This Row],[qty]]*Orders[[#This Row],[unit]]`.
"""
import sys, os, re, zipfile, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from csvtbl import parse_tbl
from a1trans import n2col

NUM=re.compile(r'^-?\d+(\.\d+)?([eE][+-]?\d+)?$')
DATE=re.compile(r'^\d{4}-\d{2}-\d{2}$')
def xesc(s): return (s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                      .replace('"','&quot;'))

def to_struct(expr, cols, tname):
    """named-column expr -> Excel structured reference. Longest name first so
    that a name which is a prefix of another is not clobbered."""
    out=expr
    for c in sorted(cols, key=len, reverse=True):
        out=re.sub(r'(?<![A-Za-z0-9_\]])'+re.escape(c)+r'(?![A-Za-z0-9_\[])',
                   f'{tname}[[#This Row],[{c}]]', out)
    return out

def build(tblpath, out, tname='Data', serial_dates=True):
    text=open(tblpath).read()
    cols, formulas, rows, aggs, key = parse_tbl(text)
    nc, nr = len(cols), len(rows)
    last=n2col(nc)
    ref=f'A1:{last}{nr+1+ (1 if aggs else 0)}'
    epoch=datetime.date(1899,12,30)

    def cell(cref, col, val, formula=None):
        if formula is not None:
            return f'<c r="{cref}"><f>{xesc(formula)}</f></c>'
        if val is None or val=='': return ''
        if DATE.match(val) and serial_dates:
            d=datetime.date.fromisoformat(val)
            return f'<c r="{cref}" s="1"><v>{(d-epoch).days}</v></c>'
        if NUM.match(val): return f'<c r="{cref}"><v>{val}</v></c>'
        return f'<c r="{cref}" t="inlineStr"><is><t>{xesc(val)}</t></is></c>'

    body=[]
    body.append('<row r="1">'+''.join(
        f'<c r="{n2col(i+1)}1" t="inlineStr" s="2"><is><t>{xesc(c)}</t></is></c>'
        for i,c in enumerate(cols))+'</row>')
    for j,r in enumerate(rows):
        rn=j+2; cs=[]
        for i,c in enumerate(cols):
            cref=f'{n2col(i+1)}{rn}'
            if c in formulas: cs.append(cell(cref,c,None,to_struct(formulas[c],cols,tname)))
            else: cs.append(cell(cref,c,r.get(c,'')))
        body.append(f'<row r="{rn}">'+''.join(cs)+'</row>')
    totals=''
    if aggs:
        rn=nr+2; cs=[]
        # totals row of the ListObject: subtotal over the table column
        FN={'sum':109,'avg':101,'count':103,'min':105,'max':104}
        acol={c:(fn,nm) for nm,(fn,c) in aggs.items()}
        for i,c in enumerate(cols):
            cref=f'{n2col(i+1)}{rn}'
            if c in acol:
                fn,_=acol[c]
                cs.append(f'<c r="{cref}"><f>SUBTOTAL({FN.get(fn,109)},{tname}[{c}])</f></c>')
            elif i==0:
                cs.append(f'<c r="{cref}" t="inlineStr"><is><t>Total</t></is></c>')
        totals=f'<row r="{rn}">'+''.join(cs)+'</row>'

    sheet=f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheetViews><sheetView tabSelected="1" workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
<sheetData>{''.join(body)}{totals}</sheetData>
<tableParts count="1"><tablePart r:id="rId1"/></tableParts>
</worksheet>'''

    tcols=''.join(
      (f'<tableColumn id="{i+1}" name="{xesc(c)}">'
       f'<calculatedColumnFormula>{xesc(to_struct(formulas[c],cols,tname))}</calculatedColumnFormula>'
       + (f'<totalsRowFunction>{[k for k,(f_,cc) in [(nm,v) for nm,v in aggs.items()] if cc==c] and ""}</totalsRowFunction>' if False else '')
       + '</tableColumn>') if c in formulas else
      f'<tableColumn id="{i+1}" name="{xesc(c)}"/>' for i,c in enumerate(cols))
    table=f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" id="1"
 name="{tname}" displayName="{tname}" ref="{ref}" totalsRowCount="{1 if aggs else 0}">
<autoFilter ref="A1:{last}{nr+1}"/>
<tableColumns count="{nc}">{tcols}</tableColumns>
<tableStyleInfo name="TableStyleMedium2" showFirstColumn="0" showLastColumn="0" showRowStripes="1" showColumnStripes="0"/>
</table>'''

    parts={
'[Content_Types].xml':'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/tables/table1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
<Override PartName="/docProps/custom.xml" ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml"/>
</Types>''',
'_rels/.rels':'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties" Target="docProps/custom.xml"/>
</Relationships>''',
'docProps/custom.xml': '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
<property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="2" name="gws.tbl"><vt:lpwstr>%s</vt:lpwstr></property>
</Properties>''' % xesc(__import__('json').dumps({'key':key,'aggs':{k:f'{v[0]}({v[1]})' for k,v in aggs.items()},
                                                 'formulas':formulas},separators=(',',':'))),
'xl/workbook.xml':'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="%s" sheetId="1" r:id="rId1"/></sheets>
<calcPr fullCalcOnLoad="1"/></workbook>''' % tname,
'xl/_rels/workbook.xml.rels':'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>''',
'xl/worksheets/sheet1.xml':sheet,
'xl/worksheets/_rels/sheet1.xml.rels':'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/table" Target="../tables/table1.xml"/>
</Relationships>''',
'xl/tables/table1.xml':table,
'xl/styles.xml':'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="1"><numFmt numFmtId="164" formatCode="yyyy\\-mm\\-dd"/></numFmts>
<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>
<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''}
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for n,c in parts.items(): z.writestr(n,c)
    return cols, formulas, rows, aggs

if __name__=='__main__':
    cols,f,r,a = build(sys.argv[1], sys.argv[2], tname=(sys.argv[3] if len(sys.argv)>3 else 'Data'))
    print(f'wrote {sys.argv[2]}: {len(r)} rows, {len(cols)} cols, '
          f'{len(f)} computed column(s) {list(f)}, {len(a)} totals {list(a)}')
