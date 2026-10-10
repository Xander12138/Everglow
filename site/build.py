"""Build review or production-candidate HTML. Local files only; never deploys."""
from pathlib import Path
from urllib.parse import urlsplit
from datetime import datetime, timezone
from html import escape, unescape
import argparse
import os
import re
import hashlib
import json
import shutil
from xml.etree.ElementTree import Element, SubElement, tostring

ROOT = Path(__file__).resolve().parent
APP = 'https://apps.apple.com/us/app/everglow-ai-journal/id6775044981'
# Same inbox the app's Settings → Support composes to.
SUPPORT = 'mailto:eightman532+everglowsupport@gmail.com'
PAGES = [
    ('home', 'index.html', '/', 'Everglow — AI journal for iPhone | Your life, in context',
     'Write, reflect and revisit your life with Everglow, an AI journal for iPhone. Cloud is optional. Understand AI processing, purchases and Markdown export.'),
    ('ai-and-privacy', 'ai-and-privacy/index.html', '/ai-and-privacy/', 'Everglow AI privacy — on-device, API key and Cloud',
     'Understand where Everglow processes journal context: on your iPhone, with an API-key provider, or through optional hosted Cloud. Backup is a separate choice.'),
    ('privacy', 'privacy/index.html', '/privacy/', 'Everglow — Privacy Policy',
     'Read Everglow’s published privacy policy.'),
    ('terms', 'terms/index.html', '/terms/', 'Everglow — Terms of Use',
     'Read Everglow’s published terms of use.'),
    ('plans', 'plans/index.html', '/plans/', 'Everglow Unlimited and Cloud — compare your options',
     'Compare Everglow’s one-time Unlimited app unlock with its optional Cloud hosted-AI subscription. See what the free limits and subscription access include.'),
    ('portability', 'portability/index.html', '/portability/', 'Everglow journal import and Markdown export',
     'Review existing entries before importing into Everglow. Learn what dated Markdown export includes, what it omits, and how it differs from snapshot backup.'),
    ('what-is-an-ai-journal', 'what-is-an-ai-journal/index.html', '/what-is-an-ai-journal/', 'What is an AI journal? How Everglow works',
     'An AI journal helps you write, then find answers and patterns across everything you’ve written. See what Everglow does with your entries, and what it doesn’t.'),
    ('offline-ai-journal', 'offline-ai-journal/index.html', '/offline-ai-journal/', 'Can an AI journal work offline? On-device AI in Everglow',
     'Everglow’s on-device mode runs AI on your iPhone after a one-time model download, so you can write and reflect without a connection.'),
    ('private-ai-journal', 'private-ai-journal/index.html', '/private-ai-journal/', 'Is an AI journal private? Where your entries go',
     'Everglow stores your journal on your iPhone. Whether AI requests leave the device depends on the engine you choose: on-device, your own API key, or optional Cloud.'),
    ('rosebud-alternative', 'rosebud-alternative/index.html', '/rosebud-alternative/', 'Rosebud alternative now the free plan has ended | Everglow',
     'Rosebud retired its free plan on 30 September 2026. Everglow is an iPhone AI journal with a one-time unlock, on-device AI or your own key, and Markdown import.'),
    ('move-from-day-one', 'move-from-day-one/index.html', '/move-from-day-one/', 'How to move your Day One journal | Everglow',
     'Export Day One as JSON and import it into Everglow: dates, text and tags carry over; photos, places and weather don’t. Steps, a format table and limits.'),
    ('own-api-key-journal', 'own-api-key-journal/index.html', '/own-api-key-journal/', 'Can I use my own API key in an AI journal? | Everglow',
     'Everglow for iPhone works with your own OpenAI, Claude, Gemini or DeepSeek API key. Unlimited is a one-time $9.99 unlock (US); your provider bills AI usage.'),
    ('on-device-ai-journal-iphone', 'on-device-ai-journal-iphone/index.html', '/on-device-ai-journal-iphone/', 'How does on-device AI journaling work on iPhone? | Everglow',
     'Everglow runs Google’s Gemma 4 E2B on your iPhone with LiteRT-LM after one 2.6 GB Wi-Fi download. What the model does, what it needs, and the trade-offs.'),
    ('not-found', '404.html', '/404.html', 'Page not found — Everglow',
     'Return to Everglow’s journal, AI options and import information.'),
]

# Answer-first question pages: linked from every footer, titled by their question (AEO).
QUESTIONS = ('what-is-an-ai-journal', 'offline-ai-journal', 'private-ai-journal')
# Longer guides (#4): footer-linked and titled like the question pages.
GUIDES = ('rosebud-alternative', 'move-from-day-one', 'own-api-key-journal', 'on-device-ai-journal-iphone')

LANGUAGES = {'en':('en','English'), 'zh':('zh-Hans','中文'), 'ja':('ja','日本語'),
             'fr':('fr','Français'), 'es':('es','Español')}
SOURCE = json.loads((ROOT/'locales/source.json').read_text())
EN_UI = {'language':'Language','main':'Main navigation','skip':'Skip to content',
         'preview':'Local review draft · Nothing published','ai-and-privacy':'AI & privacy',
         'plans':'Plans','portability':'Import & export','privacy':'Privacy policy',
         'terms':'Terms','support':'Support','footer':'© 2026 Haoyu Xu · Everglow for iPhone',
         'home':'Home','not-found':'Page not found',
         'what-is-an-ai-journal':'What is an AI journal?','offline-ai-journal':'Offline AI journal',
         'private-ai-journal':'Private AI journal',
         'on-device-ai-journal-iphone':'On-device AI on iPhone',
         'own-api-key-journal':'Use your own API key',
         'move-from-day-one':'Move from Day One',
         'rosebud-alternative':'Rosebud alternative',
         'features':['Journal timeline and search','Ask questions across your journal','AI companion chat',
                     'Pages for the people and places you write about','On-device AI, your own API key, or optional Cloud',
                     'Markdown import and export','English, Chinese, Japanese, French and Spanish']}

def translated_body(key, locale, data):
    body=(ROOT/'pages'/(key+'.html')).read_text()
    if locale=='en': return body
    index=0
    parts=re.split(r'(<[^>]+>)',body)
    for i,part in enumerate(parts):
        if part.startswith('<'):continue
        text=unescape(part.strip())
        if not text:continue
        if text=='.':
            parts[i]='。' if locale in ('zh','ja') else part
            continue
        if text!=SOURCE['pages'][key][index]:raise ValueError('Translation source changed: '+key)
        value=data['pages'][key][index];index+=1
        if locale in ('zh','ja'):parts[i]=escape(value)
        else:
            prefix=part[:len(part)-len(part.lstrip())]
            suffix=part[len(part.rstrip()):]
            parts[i]=prefix+escape(value)+suffix
    if index!=len(data['pages'][key]):raise ValueError('Missing translated text: '+key)
    body=''.join(parts)
    alts=dict(zip(SOURCE['alts'][key],data.get('alts',{}).get(key,[])))
    return re.sub(r'alt="([^"]+)"',lambda m:'alt="'+escape(alts[unescape(m[1])],quote=True)+'"',body)

def legal_body(key, locale):
    source=(ROOT/'sources'/('github-'+key+'.html')).read_text()
    if locale=='en':segments=SOURCE['legal'][key]
    elif locale=='zh':segments=SOURCE['legal_zh'][key]
    else:segments=json.loads((ROOT/'locales'/(locale+'-legal.json')).read_text())[key]
    body=source.split('<div class="wrap">',1)[1].split('  </div>\n\n  <script>',1)[0]
    index=0
    def replace(match):
        nonlocal index
        if match[1]=='zh':return ''
        value=segments[index];index+=1
        return '<span>'+value+'</span>'
    body=re.sub(r'<span data-lang="(en|zh)">(.*?)</span>',replace,body,flags=re.S)
    if index!=len(segments):raise ValueError('Missing legal segment: '+key)
    # The source's styles remain; URL-based languages replace its two-language script.
    style=re.search(r'<style>(.*?)</style>',source,re.S)[1]
    return body,style,segments

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--production',action='store_true')
parser.add_argument('--domain',default='')
args=parser.parse_args();origin=args.domain.rstrip('/')
if args.production:
    parsed=urlsplit(origin)
    if parsed.scheme!='https' or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password or parsed.port:
        raise SystemExit('Use an explicit HTTPS origin.')
elif origin:raise SystemExit('Review builds omit canonical domains.')
dist=ROOT/('release-candidate' if args.production else 'dist');dist.mkdir(exist_ok=True)
(dist/'assets').mkdir(exist_ok=True)
manifest=[]
for source in sorted((ROOT/'assets').iterdir()):
    if source.is_file():
        shutil.copyfile(source,dist/'assets'/source.name)
        manifest.append({'file':'assets/'+source.name,'bytes':source.stat().st_size,'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
shutil.copyfile(ROOT/'styles.css',dist/'style.css');shutil.copyfile(ROOT/'llms.txt',dist/'llms.txt')
# Screenshots display at ~300px: serve WebP (640w for 2x screens, full width via srcset); the PNGs stay as the lossless originals.
from PIL import Image
for shot in ('room-listing-entry','earlier-entry','companion-chat','import-preview','export'):
    image=Image.open(ROOT/'assets'/(shot+'.png')).convert('RGB')
    image.save(dist/'assets'/(shot+'.webp'),'WEBP',quality=82,method=6)
    image.resize((640,round(640*image.height/image.width)),Image.LANCZOS).save(dist/'assets'/(shot+'-640.webp'),'WEBP',quality=82,method=6)
# Browsers and crawlers request /favicon.ico regardless of the <link> icons; it was the one legitimate 404.
Image.open(ROOT/'assets'/'icon-192.png').save(dist/'favicon.ico',sizes=[(16,16),(32,32),(48,48)])
urls=[]
for locale,(html_lang,_) in LANGUAGES.items():
    data={} if locale=='en' else json.loads((ROOT/'locales'/(locale+'.json')).read_text())
    ui=EN_UI if locale=='en' else data['ui']
    locale_root=dist if locale=='en' else dist/locale
    for key,filename,path,title,description in PAGES:
        destination=locale_root/filename;destination.parent.mkdir(parents=True,exist_ok=True)
        def link(target):
            if args.production and key=='not-found':return '/'+target.relative_to(dist).as_posix()
            return os.path.relpath(target,destination.parent).replace(os.sep,'/')
        locale_path=path if locale=='en' else '/'+locale+path
        indexable=args.production and key!='not-found'
        metadata=''
        if indexable:
            canonical=origin+locale_path;urls.append(canonical)
            metadata='<link rel="canonical" href="'+canonical+'">\n<meta property="og:url" content="'+canonical+'">\n'
            for other,(code,_) in LANGUAGES.items():
                alternate=origin+(path if other=='en' else '/'+other+path)
                metadata+='<link rel="alternate" hreflang="'+code+'" href="'+alternate+'">\n'
            metadata+='<link rel="alternate" hreflang="x-default" href="'+origin+path+'">\n'
        language_links=''.join('<a lang="'+code+'" hreflang="'+code+'" href="'+link((dist if other=='en' else dist/other)/filename)+'"'+(' aria-current="page"' if other==locale else '')+'>'+label+'</a>' for other,(code,label) in LANGUAGES.items())
        language_nav='<nav class="language-nav" aria-label="'+escape(ui['language'],quote=True)+'">'+language_links+'</nav>'
        legal_style='';schema=''
        if key in ('privacy','terms'):
            body,legal_style,segments=legal_body(key,locale)
            body=body.replace('href="./index.html"','href="'+SUPPORT+'"')
            for sibling in ('privacy','terms'):body=body.replace('href="./'+sibling+'.html"','href="'+link(locale_root/sibling/'index.html')+'"')
            main='<main class="wrap" id="main">'+body+'</main>'
            header='<header class="legal-header"><a href="'+link(locale_root/'index.html')+'">← Everglow</a>'+language_nav+'</header>'
            footer=''
            if locale!='en':title='Everglow — '+segments[0];description=segments[2]
        else:
            body=translated_body(key,locale,data)
            site_base=link(dist/'assets'/'earlier-entry.png').rsplit('assets/',1)[0]
            local_base=link(locale_root/'index.html').rsplit('index.html',1)[0]
            body=body.replace('{{BASE}}assets/',site_base+'assets/').replace('{{BASE}}',local_base).replace('{{APP}}',APP)
            main='<main id="main">'+body+'</main>'
            nav=''.join('<a href="'+link(locale_root/slug/'index.html')+'"'+(' aria-current="page"' if key==slug else '')+'>'+escape(ui[slug])+'</a>' for slug in ('ai-and-privacy','plans','portability'))
            header='<header><nav class="wrap" aria-label="'+escape(ui['main'],quote=True)+'"><a class="brand" href="'+link(locale_root/'index.html')+'"><img class="brand-icon" src="'+link(dist/'assets'/'icon-192.png')+'" width="32" height="32" alt=""><span>e</span>verglow</a><div class="navlinks">'+nav+'</div></nav>'+language_nav+'</header>'
            footer='<footer><div class="wrap footer-inner"><span>'+escape(ui['footer'])+'</span><div class="footerlinks"><a href="'+SUPPORT+'">'+escape(ui['support'])+'</a><a href="'+link(locale_root/'privacy/index.html')+'">'+escape(ui['privacy'])+'</a><a href="'+link(locale_root/'terms/index.html')+'">'+escape(ui['terms'])+'</a>'+''.join('<a href="'+link(locale_root/q/'index.html')+'">'+escape(ui[q])+'</a>' for q in QUESTIONS+GUIDES)+'</div></div></footer>'
            if locale!='en':
                texts=data['pages'][key]
                if key=='home':heading=(texts[1]+('' if locale in ('zh','ja') else ' ')+texts[2]).rstrip('。.')
                else:heading=texts[1]+(' '+texts[2] if key in ('ai-and-privacy','portability','not-found') else '')
                title='Everglow — '+heading;description=texts[2 if key=='plans' else 3]
                if key in QUESTIONS+GUIDES:title=texts[1]+' | Everglow: AI Journal';description=texts[2]
            graph=[]
            if key=='home':
                app={'@context':'https://schema.org','@type':'SoftwareApplication','name':'Everglow: AI Journal','operatingSystem':'iOS','applicationCategory':'LifestyleApplication','installUrl':APP,'description':description,'inLanguage':html_lang,
                     'offers':{'@type':'Offer','price':'0','priceCurrency':'USD','description':'Free download with in-app purchases'},
                     'featureList':ui['features'],'publisher':{'@type':'Person','name':'Haoyu Xu'},
                     # "Everglow" alone is shared with a K-pop group; give search and AI engines the app's full name and its App Store identity.
                     'alternateName':['Everglow AI Journal','Everglow'],'sameAs':[APP],
                     'disambiguatingDescription':'An AI journaling app for iPhone by Haoyu Xu. Not related to the K-pop group EVERGLOW.'}
                if indexable:
                    app['url']=origin+locale_path
                    app['screenshot']=[origin+'/assets/'+a for a in ('room-listing-entry.png','earlier-entry.png','companion-chat.png','import-preview.png','export.png')]
                graph.append(app)
                site={'@context':'https://schema.org','@type':'WebSite','name':'Everglow: AI Journal','alternateName':['Everglow AI Journal','Everglow'],'inLanguage':html_lang}
                if indexable:site['url']=origin+'/'
                graph.append(site)
            # Built from the visible FAQ, never hidden-only, so markup and page always agree.
            faqs=re.findall(r'<details><summary>(.*?)</summary><p>(.*?)</p></details>',body,re.S)
            plain=lambda h:unescape(re.sub(r'<[^>]+>','',h)).strip()
            if faqs:graph.append({'@context':'https://schema.org','@type':'FAQPage','inLanguage':html_lang,'mainEntity':[{'@type':'Question','name':plain(q),'acceptedAnswer':{'@type':'Answer','text':plain(a)}} for q,a in faqs]})
            if key in QUESTIONS+GUIDES and indexable:
                home_url=origin+('/' if locale=='en' else '/'+locale+'/')
                graph.append({'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[
                    {'@type':'ListItem','position':1,'name':ui['home'],'item':home_url},
                    {'@type':'ListItem','position':2,'name':ui[key],'item':origin+locale_path}]})
            schema=''.join('<script type="application/ld+json">'+json.dumps(g,ensure_ascii=False).replace('</','<\\/')+'</script>' for g in graph)
        # Link previews need absolute URLs, so only the production build names its card (make_og.py renders one per locale).
        share_image=''
        if args.production:
            card=origin+'/assets/og-'+locale+'.png'
            share_image=('<meta property="og:image" content="'+card+'"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
                         '<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="'+card+'">\n')
        robots='index,follow' if indexable else 'noindex,follow'
        banner='' if args.production else '<div class="preview">'+escape(ui['preview'])+'</div>'
        document=f'''<!doctype html>
<html lang="{html_lang}">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><meta name="description" content="{escape(description,quote=True)}">
<meta name="robots" content="{robots}"><meta name="apple-itunes-app" content="app-id=6775044981"><meta name="msvalidate.01" content="73882E46817FEBD890296607D8E70152"><meta name="theme-color" content="#f7f0df">
<meta property="og:type" content="website"><meta property="og:site_name" content="Everglow: AI Journal">
<meta property="og:title" content="{escape(title,quote=True)}"><meta property="og:description" content="{escape(description,quote=True)}">
{metadata}{share_image}<link rel="stylesheet" href="{link(dist/'style.css')}"><link rel="icon" type="image/png" sizes="32x32" href="{link(dist/'assets'/'icon-32.png')}"><link rel="icon" type="image/png" sizes="192x192" href="{link(dist/'assets'/'icon-192.png')}"><link rel="apple-touch-icon" href="{link(dist/'assets'/'apple-touch-icon.png')}">
<style>{legal_style}</style>
</head><body><a class="skip" href="#main">{escape(ui['skip'])}</a>{banner}{header}{main}{footer}{schema}</body></html>
'''
        destination.write_text(document)
if args.production:
    (dist/'robots.txt').write_text('User-agent: *\nAllow: /\n\nSitemap: '+origin+'/sitemap.xml\n')
    root=Element('urlset',xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for url in urls:SubElement(SubElement(root,'url'),'loc').text=url
    (dist/'sitemap.xml').write_bytes(tostring(root,encoding='utf-8',xml_declaration=True))
else:
    (dist/'robots.txt').write_text('User-agent: *\nAllow: /\n# Review HTML carries noindex.\n');(dist/'sitemap.xml').unlink(missing_ok=True)
headers='/*\n  Cache-Control: public, max-age=0, must-revalidate, no-transform\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n'
if not args.production:headers+='  X-Robots-Tag: noindex\n'
for locale in LANGUAGES:headers+=('/404.html' if locale=='en' else '/'+locale+'/404.html')+'\n  X-Robots-Tag: noindex\n'
# Assets keep their names when replaced, so a week (not immutable); detach the global no-cache policy first.
headers+='/assets/*\n  ! Cache-Control\n  Cache-Control: public, max-age=604800, no-transform\n'
(dist/'_headers').write_text(headers)
receipt={'mode':'production-candidate' if args.production else 'local-review','origin':origin or None,'domain_ownership_verified':False,'published':False,'output':str(dist),'locales':list(LANGUAGES),'assets':manifest,'files':[{'path':str(p.relative_to(dist)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(dist.rglob('*')) if p.is_file()]}
(ROOT/('production-build.json' if args.production else 'review-build.json')).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'mode':receipt['mode'],'files':len(receipt['files']),'bytes':sum(x['bytes'] for x in receipt['files']),'locales':list(LANGUAGES),'published':False}))
