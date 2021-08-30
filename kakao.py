from selenium import webdriver
import time
import requests
import base64
import os
import io
from PIL import Image
import json

SCROLL_PAUSE_SEC = 1
WAIT_LOAD_SEC = 3
WAIT_COMMENT_SEC = 0.5
WAIT_DELAY_SEC = 3
last_height = 0

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
    'Accept-Language': 'ko'
}

ids = []

infoURL = 'https://gateway-kw.kakao.com/section/v1/pages/novel-weekdays'
c = requests.get(infoURL, headers=headers).json()['data']['sections'][0]['cardGroups'][0]['cards']
for i in c:
    ids.append(i['content']['id'])

infoURL = 'https://gateway-kw.kakao.com/section/v1/pages/general-weekdays'
c = requests.get(infoURL, headers=headers).json()['data']['sections'][0]['cardGroups'][0]['cards']
for i in c:
    ids.append(i['content']['id'])

driver = webdriver.Chrome(executable_path='chromedriver.exe')


def get_file_content_chrome(driver, uri):
    result = driver.execute_async_script("""
    var uri = arguments[0];
    var callback = arguments[1];
    var toBase64 = function(buffer){for(var r,n=new Uint8Array(buffer),t=n.length,a=new Uint8Array(4*Math.ceil(t/3)),i=new Uint8Array(64),o=0,c=0;64>c;++c)i[c]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".charCodeAt(c);for(c=0;t-t%3>c;c+=3,o+=4)r=n[c]<<16|n[c+1]<<8|n[c+2],a[o]=i[r>>18],a[o+1]=i[r>>12&63],a[o+2]=i[r>>6&63],a[o+3]=i[63&r];return t%3===1?(r=n[t-1],a[o]=i[r>>2],a[o+1]=i[r<<4&63],a[o+2]=61,a[o+3]=61):t%3===2&&(r=(n[t-2]<<8)+n[t-1],a[o]=i[r>>10],a[o+1]=i[r>>4&63],a[o+2]=i[r<<2&63],a[o+3]=61),new TextDecoder("ascii").decode(a)};
    var xhr = new XMLHttpRequest();
    xhr.responseType = 'arraybuffer';
    xhr.onload = function(){ callback(toBase64(xhr.response)) };
    xhr.onerror = function(){ callback(xhr.status) };
    xhr.open('GET', uri);
    xhr.send();
    """, uri)
    if type(result) == int:
        raise Exception("Request failed with status %s" % result)
    return base64.b64decode(result)


def get_file(src):
    return requests.get(src, headers=headers).content


it = 0
for webtoonId in ids:
    try:
        infoURL = 'https://gateway-kw.kakao.com/decorator/v1/decorator/contents/%s' % webtoonId
        listURL = 'https://gateway-kw.kakao.com/episode/v1/views/content-home/contents/%s/episodes?sort=-NO&offset=0&limit=3000' % webtoonId
        webtoonInfo = requests.get(infoURL, headers=headers).json()['data']
        title = webtoonInfo['title']
        thumbnailSrc = webtoonInfo['sharingThumbnailImage'] + '.webp'
        description = webtoonInfo['synopsis']
        listData = requests.get(listURL, headers=headers).json()['data']['episodes']

        data_io = io.BytesIO(get_file(thumbnailSrc))
        img = Image.open(data_io).convert("RGB")
        os.makedirs(os.path.dirname('res/%s/thumbnail/main.jpg' % title), exist_ok=True)
        img.save('res/%s/thumbnail/main.jpg' % title, "JPEG")

        data = []
        digits = len(str(len(listData)))
        for (cnt, k) in enumerate(listData):
            if not k['readable']:
                continue
            oneComicURL = "https://webtoon.kakao.com/viewer/view/%s" % str(k['id'])
            driver.get(url=oneComicURL)
            time.sleep(WAIT_LOAD_SEC)
            oneTitle = driver.execute_script(
                "return document.querySelector('main>div>div>div>div>div:nth-child(2)>div>p').textContent")
            imageCount = driver.execute_script(
                "return document.querySelectorAll('.page>div>div>div>div>div>div>div>img').length")
            imgList = []
            for i in range(imageCount):
                imgSrc = driver.execute_script(
                    "return document.querySelectorAll('.page>div>div>div>div>div>div>div>img')[%d].src" % i)
                data_io = io.BytesIO(get_file_content_chrome(driver, imgSrc))
                img = Image.open(data_io).convert("RGB")
                imgList.append(img)

            filename = "res/%%s/%%s_%%0%dd.pdf" % digits % (title, title, cnt + 1)
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            imgList[0].save(filename, "PDF", save_all=True,
                            append_images=imgList[1:])

            driver.execute_script("document.querySelectorAll('button')[7].click()")
            time.sleep(WAIT_COMMENT_SEC)

            thumbnailSrc = k['asset']['thumbnailImage'] + '.webp'
            data_io = io.BytesIO(get_file(thumbnailSrc))
            img = Image.open(data_io).convert("RGB")
            os.makedirs(os.path.dirname('res/%s/thumbnail/%d.jpg' % (title, cnt + 1)), exist_ok=True)
            img.save('res/%s/thumbnail/%d.jpg' % (title, cnt), "JPEG")

            data.append({'fileName': "%%s_%%0%dd.pdf" % digits % (title, cnt + 1), 'title': oneTitle,
                         'thumbnail': 'thumbnail/%d.jpg' % (cnt + 1),
                         'comment': json.loads(driver.execute_script("""var comments=[]
        for(let i=0;i<document.querySelectorAll('.ReactModalPortal>div>div>div>div:nth-child(4)>div li').length;i++) {
            comments.push({
                nick:document.querySelectorAll('.ReactModalPortal>div>div>div>div:nth-child(4)>div li>div>div:nth-child(2) p:nth-child(2)')[i].textContent,
                content:document.querySelectorAll('.ReactModalPortal>div>div>div>div:nth-child(4)>div li>div>div:nth-child(2) p:nth-child(1)')[i].textContent,
                like:parseInt(document.querySelectorAll('.ReactModalPortal>div>div>div>div:nth-child(4)>div li>div>div:nth-child(2) button:nth-child(1)>span')[i].textContent.replace(/[^0-9]/g, '')||0),
                unlike:parseInt(document.querySelectorAll('.ReactModalPortal>div>div>div>div:nth-child(4)>div li>div>div:nth-child(2) button:nth-child(2)>span')[i].textContent.replace(/[^0-9]/g, '')||0)
            })
        }
        return JSON.stringify(comments)"""))})
            time.sleep(WAIT_DELAY_SEC)
            break

        with open('res/%s/data.json' % title, 'w', encoding='UTF-8') as fp:
            json.dump({'title': title, 'platform': 'kakao', 'description': description, 'episodes': data,
                       'thumbnail': 'thumbnail/main.jpg'}, fp, indent=4,
                      ensure_ascii=False)
    except:
        pass

    it += 1
    print('%s Done. (%d/%d)' % (webtoonId, it, len(ids)))

driver.close()
