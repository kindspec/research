"""Regenerate the three image corpora used by measure.sh (they are not committed).
   python3 regenerate.py   then   bash measure.sh png|ppm ; bash m3.sh svg"""
from PIL import Image, ImageDraw
import os, random
random.seed(7)
os.makedirs('png',exist_ok=True); os.makedirs('ppm',exist_ok=True)
os.makedirs('flat',exist_ok=True); os.makedirs('svg',exist_ok=True)
W,H=1400,1000
base=Image.frombytes('RGB',(W,H),bytes(random.getrandbits(8) for _ in range(W*H*3)))
for i in range(21):
    im=base.copy(); dd=ImageDraw.Draw(im); x0=50+i*30
    dd.rectangle([x0,50,x0+100,120], fill=(255,0,0)); dd.text((x0+10,60),"v%d"%i,fill=(255,255,255))
    im.save('png/diagram-%02d.png'%i); im.save('ppm/diagram-%02d.ppm'%i)
FW,FH=4000,3000
fb=Image.new('RGB',(FW,FH),(250,250,250)); d=ImageDraw.Draw(fb)
for i in range(200):
    x=(i*37)%(FW-300); y=(i*53)%(FH-200)
    d.rectangle([x,y,x+280,y+160], outline=(20,20,20), width=3, fill=(230,238,246))
    d.line([x,y,x+280,y+160], fill=(200,40,40), width=2)
for i in range(21):
    im=fb.copy(); dd=ImageDraw.Draw(im); x0=100+i*40
    dd.rectangle([x0,40,x0+300,180], fill=(255,90,90), outline=(0,0,0), width=4)
    im.save('flat/diagram-%02d.png'%i)
head='<svg xmlns="http://www.w3.org/2000/svg" width="4000" height="3000">\n'
body=''.join('  <rect id="r%d" x="%d" y="%d" width="280" height="160" fill="#e6eef6" stroke="#141414"/>\n'%(i,(i*37)%3700,(i*53)%2800) for i in range(200))
for i in range(21):
    open('svg/diagram-%02d.svg'%i,'w').write(head+body+'  <rect id="annot" x="%d" y="40" width="300" height="140" fill="#ff5a5a"/>\n</svg>\n'%(100+i*40))
