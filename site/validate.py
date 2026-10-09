"""Check assets, metadata, internal links and crawl staging without network or a browser."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from xml.etree import ElementTree
import json
import hashlib
import re

ROOT = Path(__file__).resolve().parent
errors = []
def check(condition, message):
    if not condition:
        errors.append(message)

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs=[];self.ids=[];self.meta={};self.canonicals=[];self.alternates={};self.anchors=[]
        self.h1=0;self.main=0;self.scripts=[];self.script=None;self.script_data='';self.lang=None;self.images=[]
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        if 'id' in d:self.ids.append(d['id'])
        if tag=='html':self.lang=d.get('lang')
        if tag=='h1':self.h1+=1
        if tag=='main':self.main+=1
        if tag=='meta':self.meta[d.get('name',d.get('property',''))]=d.get('content')
        if tag=='img':self.images.append(d)
        if tag=='link' and d.get('rel')=='canonical':self.canonicals.append(d.get('href'))
        if tag=='link' and d.get('rel')=='alternate':self.alternates[d.get('hreflang')]=d.get('href')
        if tag=='a':self.anchors.append(d)
        for attr in ['src','href']:
            if attr in d and d.get('rel')!='canonical':self.refs.append(d[attr])
        if tag=='script':self.script=d;self.script_data=''
    def handle_data(self, text):
        if self.script is not None:self.script_data+=text
    def handle_endtag(self, tag):
        if tag=='script' and self.script is not None:
            self.scripts.append((self.script,self.script_data));self.script=None

reports=[]
for directory, production in [('dist',False),('release-candidate',True)]:
    dist=ROOT/directory;pages={}
    # The approved global policy must survive every rebuild in both output modes.
    headers=(dist/'_headers').read_text()
    global_headers=headers.split('/404.html',1)[0].splitlines()
    check(global_headers[0]=='/*' and
          [line for line in global_headers if line.strip().startswith('Cache-Control:')]==
          ['  Cache-Control: public, max-age=0, must-revalidate, no-transform'],
          directory+' must retain the approved global no-transform cache policy')
    for file in dist.rglob('*.html'):
        page=Page();page.feed(file.read_text());pages[file.resolve()]=page
        label=directory+'/'+str(file.relative_to(dist))
        relative=file.relative_to(dist);locale=relative.parts[0] if relative.parts[0] in ('zh','ja','fr','es') else 'en'
        code={'en':'en','zh':'zh-Hans','ja':'ja','fr':'fr','es':'es'}[locale]
        check(page.lang==code,label+' language')
        check(page.h1==1 and page.main==1,label+' landmarks')
        check(len(page.ids)==len(set(page.ids)),label+' duplicate ids')
        check(bool(page.meta.get('description')),label+' description')
        check('{{' not in file.read_text(),label+' unresolved template')
        is404=file.name=='404.html'
        check(('noindex' in page.meta.get('robots',''))==(not production or is404),label+' robots mismatch')
        check(len(page.canonicals)==(1 if production and not is404 else 0),label+' canonical count')
        local_parts=relative.parts if locale=='en' else relative.parts[1:]
        locale_file=Path(*local_parts)
        codes={'en':'en','zh':'zh-Hans','ja':'ja','fr':'fr','es':'es'}
        route='/' if locale_file.as_posix()=='index.html' else '/'+locale_file.as_posix().removesuffix('index.html')
        expected={code:'https://everglow.cc'+(route if lang=='en' else '/'+lang+route) for lang,code in codes.items()}
        expected['x-default']='https://everglow.cc'+route
        check(page.alternates==(expected if production and not is404 else {}),label+' hreflang map')
        if production and not is404:check(page.canonicals==[expected[codes[locale]]],label+' canonical locale')
        language_links=[a for a in page.anchors if a.get('hreflang') in codes.values()]
        check(len(language_links)==5,label+' language navigation coverage')
        check(sum(a.get('aria-current')=='page' for a in language_links)==1,label+' selected language')
        for anchor in language_links:
            lang=next(k for k,v in codes.items() if v==anchor['hreflang'])
            url=urlsplit(anchor['href'])
            destination=(dist/unquote(url.path).lstrip('/')).resolve() if url.path.startswith('/') else (file.parent/unquote(url.path)).resolve()
            expected_file=(dist if lang=='en' else dist/lang)/locale_file
            check(destination==expected_file.resolve(),label+' language link changes page')
            check(anchor.get('lang')==codes[lang],label+' language link accessibility')

        for attrs in page.images:
            # The app icon is decorative beside the wordmark/button: empty alt keeps screen readers from repeating "Everglow".
            if '/icon-' in (attrs.get('src') or '') or (attrs.get('src') or '').startswith('icon-'):
                check(attrs.get('alt')=='' and attrs.get('width')==attrs.get('height') and bool(attrs.get('width')),label+' icon dimensions/alt')
            else:
                check(bool(attrs.get('alt')) and attrs.get('width')=='1206' and attrs.get('height')=='2622',label+' image dimensions/alt')
        for attrs,data in page.scripts:
            check(attrs.get('type')=='application/ld+json' and 'src' not in attrs,label+' executable/external script')
            try:json.loads(data)
            except ValueError:errors.append(label+' invalid JSON-LD')
    for file,page in pages.items():
        for ref in page.refs:
            url=urlsplit(ref)
            if url.scheme or url.netloc:continue
            if url.path.startswith('/'):
                dest=(dist/unquote(url.path).lstrip('/')).resolve()
            else:
                dest=(file.parent/unquote(url.path)).resolve() if url.path else file
            check(dist.resolve()==dest or dist.resolve() in dest.parents,str(file)+' reference escapes output: '+ref)
            check(dest.is_file(),str(file)+' missing reference: '+ref)
            if url.fragment and dest in pages:
                check(unquote(url.fragment) in pages[dest].ids,str(file)+' missing anchor: '+ref)
    canonical_urls={url for page in pages.values() for url in page.canonicals}
    if production:
        sitemap=ElementTree.parse(dist/'sitemap.xml')
        listed={node.text for node in sitemap.findall('.//{*}loc')}
        check(listed==canonical_urls,'Production sitemap differs from canonical pages')
        check('Sitemap: https://everglow.cc/sitemap.xml' in (dist/'robots.txt').read_text(),'Production robots sitemap')
        check('Disallow: /' not in (dist/'robots.txt').read_text(),'Production blocked robots')
        check('X-Robots-Tag: noindex' not in (dist/'_headers').read_text().split('/404.html')[0],'Production global noindex')
    else:
        check(not (dist/'sitemap.xml').exists(),'Review sitemap must be absent')
        check('X-Robots-Tag: noindex' in (dist/'_headers').read_text(),'Review noindex header')
        check('Disallow: /' not in (dist/'robots.txt').read_text(),'Review crawlers cannot see noindex')
    file_count=sum(1 for f in dist.rglob('*') if f.is_file())
    max_size=max(f.stat().st_size for f in dist.rglob('*') if f.is_file())
    check(file_count<20_000 and max_size<25*1024*1024,directory+' exceeds Cloudflare static asset limits')
    reports.append({'directory':directory,'html_pages':len(pages),'internal_links_verified':True,'metadata_verified':True,'asset_files':file_count,'largest_file_bytes':max_size})
legal_reports=[]
source_catalog=json.loads((ROOT/'locales/source.json').read_text())
for key,blob in [('privacy','47b4b9736645adb5045a59f50aacd102e4a46dd4'),('terms','acb905be5098ddae54bdff020a111fca7ee6bb58')]:
    raw=(ROOT/'sources'/('github-'+key+'.html')).read_bytes()
    check(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob,key+' source changed from inspected GitHub blob')
    original=raw.decode()
    for locale in ('en','zh','ja','fr','es'):
        if locale in ('en','zh'):
            expected=re.findall(r'<span data-lang="'+locale+r'">(.*?)</span>',original,re.S)
        else:expected=json.loads((ROOT/'locales'/(locale+'-legal.json')).read_text())[key]
        check(len(expected)==len(source_catalog['legal'][key]),locale+'/'+key+' missing legal clause')
        for directory in ('dist','release-candidate'):
            folder=ROOT/directory if locale=='en' else ROOT/directory/locale
            text=(folder/key/'index.html').read_text()
            main=text.split('<main class="wrap" id="main">',1)[1].split('</main>',1)[0]
            actual=re.findall(r'<span>(.*?)</span>',main,re.S)
            check(actual==expected,directory+'/'+locale+'/'+key+' legal segment parity')
            for reference,translation in zip(source_catalog['legal'][key],expected):
                rp=Page();rp.feed(reference);tp=Page();tp.feed(translation)
                check(rp.refs==tp.refs,locale+'/'+key+' changed legal external link')
            date='18' if key=='privacy' else '27'
            check('2026' in expected[1] and date in expected[1],locale+'/'+key+' legal date')
        legal_reports.append({'locale':locale,'document':key,'github_blob_sha':blob,'all_legal_clauses_rendered':True,'original_wording_parity':locale in ('en','zh'),'translation_substance_independently_reviewed':False})
for locale in ('zh','ja','fr','es'):
    data=json.loads((ROOT/'locales'/(locale+'.json')).read_text())
    for key,texts in source_catalog['pages'].items():
        check(len(data['pages'][key])==len(texts),locale+'/'+key+' product translation missing')
        check(len(data.get('alts',{}).get(key,[]))==len(source_catalog['alts'][key]),locale+'/'+key+' image alt translation missing')
terminology=json.loads((ROOT/'sources/app-terminology.json').read_text())
app_labels=next(item['localized'] for item in terminology['terms'] if item['source']=='Unlimited')
for locale in ('ja','fr','es'):
    data=json.loads((ROOT/'locales'/(locale+'.json')).read_text())
    label=app_labels[locale]
    for key in ('home','plans'):
        text='\n'.join(data['pages'][key])
        check('Everglow Unlimited' in text and label in text,locale+'/'+key+' missing app-label mapping')
        qualified='Everglow Unlimited（'+label+'）' if locale=='ja' else 'Everglow Unlimited ('+label+')'
        check('Unlimited' not in text.replace(qualified,''),locale+'/'+key+' unmapped Unlimited label')
ja_legal=json.loads((ROOT/'locales/ja-legal.json').read_text())
check(all('初期設定では' in ja_legal['privacy'][i] and '通常' not in ja_legal['privacy'][i] for i in (4,10)),
      'Japanese default-setting qualification must not become usually')
provenance=json.loads((ROOT/'asset-provenance.json').read_text())
for item in provenance:
    for folder in ['assets','dist/assets','release-candidate/assets']:
        f=ROOT/folder/Path(item['asset']).name
        check(hashlib.sha256(f.read_bytes()).hexdigest()==item['sha256'],str(f)+' changed source image')
result={'passed':not errors,'errors':errors,'builds':reports,'assets_identical_to_sources':not errors,
        'legal_content_parity':legal_reports,
        'browser_visual_qa':'Five-language candidate not yet browser reviewed. Previous English/bilingual review is historical; locale layout, URL language navigation, 761px and 200% zoom need review. This validator is static.',
        'runtime_or_live_claims_verified':False,'published':False}
(ROOT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(bool(errors))
