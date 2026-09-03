"""Does an agent's captured anchor survive an UNRELATED upstream edit?
Metric: not 'is the anchor unique now' but 'does it still exist after someone
else edits elsewhere'. Run: python3 survival.py"""
import textwrap
sents=["Procurement totalled 660.00 against a plan of 500.00.",
 "The overage is concentrated in the widget line, which doubled in Q3.",
 "We reviewed the gadget contract and found no comparable increase.",
 "The flange order was placed twice and one instance has been cancelled.",
 "Finance has asked for a revised forecast before the board meeting.",
 "The overage is concentrated in the widget line, which doubled in Q3."]
after=list(sents); after[0]="Procurement totalled exactly 660.00 against a plan of 500.00."
wrap=lambda ss: textwrap.fill(" ".join(ss),72).splitlines()
sem =lambda ss: list(ss)
for tag,fn,anchor in [
  ("wrapped ",wrap,"placed twice and one instance has been cancelled. Finance has asked for"),
  ("semantic",sem ,"The flange order was placed twice and one instance has been cancelled.")]:
    b,a=fn(sents),fn(after)
    print(f"{tag}: anchor survives={anchor in chr(10).join(a)!s:5s} "
          f"lines changed by the one-word upstream edit={sum(1 for x,y in zip(b,a) if x!=y)} of {len(b)}")
