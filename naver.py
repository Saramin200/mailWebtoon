import io
from selenium import webdriver
from PIL import Image
import os
import json
import requests
from urllib.parse import urlparse, parse_qs
import datetime
import pathvalidate
import time

driver = webdriver.Chrome(executable_path='chromedriver.exe')

infoURL = 'https://comic.naver.com/webtoon/weekday'
driver.get(url=infoURL)
ids = driver.execute_script('''return Array.from(document.querySelectorAll('.col_inner')[%d].querySelectorAll('a.title')).map(el=>{
    return new URL(el.href).searchParams.get('titleId')
})''' % datetime.datetime.today().weekday())


def get_file(src, referer):
    headers = {'Referer': referer}
    return requests.get(src, headers=headers).content


it = 0

for webtoonId in ids:
    try:
        infoURL = 'https://comic.naver.com/webtoon/list?titleId=%s' % webtoonId
        driver.get(url=infoURL)
        title = driver.execute_script("return document.querySelector(`meta[property='og:title']`).getAttribute('content')")
        title = pathvalidate.replace_symbol(title)
        thumbnailSrc = driver.execute_script("return document.querySelector('.thumb img').src")
        data_io = io.BytesIO(get_file(thumbnailSrc, "https://comic.naver.com/webtoon/list?titleId=%s" % webtoonId))
        img = Image.open(data_io).convert("RGB")
        os.makedirs(os.path.dirname('res/%s/thumbnail/main.jpg' % title), exist_ok=True)
        img.save('res/%s/thumbnail/main.jpg' % title, "JPEG")

        episodes = []
        i = 1
        while True:
            detailURL = "https://comic.naver.com/webtoon/list?titleId=%s&page=%d" % (webtoonId, i)
            driver.get(url=detailURL)
            if str(i) != driver.execute_script(
                    "return document.querySelector('.page .blind').parentElement.querySelector('.num_page').textContent"):
                break
            episodes += driver.execute_script("""let li=[];for(let i of document.querySelectorAll('tbody tr:not(.band_banner)')) {
                li.push({link:i.querySelector('a').href,
                         thumbnail:i.querySelector('img').src
                        })
            }
            return li""")
            break

        episodes = episodes[:1]
        data = []
        digits = len(str(len(episodes)))
        parsed_url = urlparse(episodes[0]['link'])
        cnt = int(parse_qs(parsed_url.query)['no'][0])
        for k in episodes:
            oneComicURL = k['link']
            driver.get(url=oneComicURL)
            time.sleep(1)

            oneTitle = driver.execute_script("return document.querySelector('.tit_area h3').textContent")
            date = driver.execute_script("return document.querySelector('.vote_lst .rt dd.date').textContent")
            star = driver.execute_script("return document.querySelector('#topPointTotalNumber strong').textContent")

            data_io = io.BytesIO(get_file(k['thumbnail'], oneComicURL))
            img = Image.open(data_io).convert("RGB")
            os.makedirs(os.path.dirname('res/%s/thumbnail/%d.jpg' % (title, cnt)), exist_ok=True)
            img.save('res/%s/thumbnail/%d.jpg' % (title, cnt), "JPEG")

            imageCount = driver.execute_script(
                "return document.querySelectorAll('.wt_viewer img').length")

            imgList = []
            for i in range(imageCount):
                imgSrc = driver.execute_script(
                    "return document.querySelectorAll('.wt_viewer img')[%d].src" % i)
                data_io = io.BytesIO(get_file(imgSrc, oneComicURL))
                img = Image.open(data_io).convert("RGB")
                imgList.append(img)

            filename = "res/%%s/%%s_%%0%dd.pdf" % digits % (title, title, cnt)
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            imgList[0].save(filename, "PDF", save_all=True,
                            append_images=imgList[1:])

            commentURL = driver.execute_script("return document.querySelector('#commentIframe').src")
            driver.get(url=commentURL)

            data.append(
                {'fileName': "%%s_%%0%dd.pdf" % digits % (title, cnt), 'title': oneTitle, 'date': date, 'star': star,
                 'thumbnail': 'thumbnail/%d.jpg' % cnt,
                 'comment': driver.execute_script("""var comments=[]
                for(let i=0;i<document.querySelectorAll('.u_cbox_comment_box .u_cbox_contents').length;i++) {
                    comments.push({
                        nick:document.querySelectorAll('.u_cbox_comment_box .u_cbox_nick')[i].textContent,
                        content:document.querySelectorAll('.u_cbox_comment_box .u_cbox_contents')[i].textContent,
                        like:parseInt(document.querySelectorAll('.u_cbox_cnt_recomm')[i].textContent),
                        unlike:parseInt(document.querySelectorAll('.u_cbox_cnt_unrecomm')[i].textContent)
                    })
                }
                return comments""")})
            cnt = cnt + 1

        os.makedirs(os.path.dirname('res/%s/data.json' % title), exist_ok=True)
        with open('res/%s/data.json' % title, 'w', encoding='UTF-8') as fp:
            json.dump({'title': title, 'platform': 'naver', 'episodes': data, 'thumbnail': 'thumbnail/main.jpg'}, fp,
                      indent=4, ensure_ascii=False)
    except:
        pass
    it += 1
    print('%s Done. (%d/%d)' % (webtoonId, it, len(ids)))

driver.close()
