import re
import time
from pathlib import Path
from urllib.parse import unquote, urljoin

import truststore

truststore.inject_into_ssl()

import requests  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402
from tqdm import tqdm  # noqa: E402

LIST_URL = "https://www.ceec.edu.tw/xmfile/indexaction"
TIMEOUT = 30
RETRY = 3

SOURCES = [
    {
        "name": "GSAT",
        "index": "https://www.ceec.edu.tw/xmfile?xsmsid=0J052424829869345634",
        "cat": "0J075836833990807814",
    },
    {
        "name": "AST",
        "index": "https://www.ceec.edu.tw/xmfile?xsmsid=0J052427633128416650",
        "cat": "0J052434223167797250",
    },
]

SPECIAL_FILES = [
    {
        "url": "https://www.ceec.edu.tw/files/file_pool/1/0J053430863374769111/03-01-107%E5%AD%B8%E6%B8%AC%E8%8B%B1%E6%96%87%E5%8F%83%E8%80%83%E8%A9%A6%E5%8D%B7%28%E5%AE%9A%E7%A8%BF%29.pdf",
        "year": 107,
        "type": "GSAT_REF",
    },
    {
        "url": "https://www.ceec.edu.tw/files/file_pool/1/0L251351892018529090/02-110%E8%A9%A6%E8%BE%A6%E8%80%83%E8%A9%A6%E8%8B%B1%E6%96%87%E8%A9%A6%E5%8D%B7%E5%AE%9A%E7%A8%BF.pdf",
        "year": 110,
        "type": "GSAT_TRIAL",
    },
    {
        "url": "https://www.ceec.edu.tw/files/file_pool/1/0M263619256746092628/111%E5%AD%B8%E5%B9%B4%E5%BA%A6%E7%94%A8%E5%AD%B8%E6%B8%AC%E8%8B%B1%E6%96%87%E8%80%83%E7%A7%91%E5%8F%83%E8%80%83%E8%A9%A6%E5%8D%B7.pdf",
        "year": 111,
        "type": "GSAT_REF",
    },
    # https://www.ceec.edu.tw/xmdoc/cont?xsmsid=0J018586101460336585&sid=0O211573150658099894
    {
        "url": "https://www.ceec.edu.tw/files/file_pool/1/0O211576602559573811/02_02_%E5%AD%B8%E6%B8%AC%E8%8B%B1%E6%96%87%E8%80%83%E7%A7%91115%E8%B5%B7%E9%81%A9%E7%94%A8%E5%8F%83%E8%80%83%E8%A9%A6%E5%8D%B7.pdf",
        "year": 115,
        "type": "GSAT_REF",
    },
]

ALLOW_EXT = {".pdf", ".doc", ".docx"}
KEEP_RE = re.compile(r"試題|試卷")
DROP_RE = re.compile(r"答題卷|答案|評分|非選擇")


def sanitize(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", s)


def download(session: requests.Session, url: str, path: Path) -> bool:
    path.parent.mkdir(exist_ok=True, parents=True)
    if path.exists():
        return True

    tmp = path.with_suffix(".part")
    for n in range(1, RETRY + 1):
        try:
            with session.get(url, stream=True, timeout=TIMEOUT) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                bar = tqdm(total=total, unit="B", unit_scale=True, desc=path.name, leave=False)
                with tmp.open("wb") as f:
                    for chunk in r.iter_content(8192):
                        if chunk:
                            f.write(chunk)
                            bar.update(len(chunk))
                bar.close()
            tmp.rename(path)
            return True
        except Exception as e:
            print(f"Download error {n}/{RETRY}: {e}")
            time.sleep(1)
    return False


def hidden_inputs(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    return {
        str(i["name"]): str(i.get("value", ""))
        for i in soup.select("form#MainForm input[type=hidden]")
    }


def fetch_page(session: requests.Session, base: dict, page: int, cat_id: str) -> str:
    data = base.copy()
    data.update(
        {
            "CatSId": cat_id,
            "ExecAction": "Q",
            "IndexOfPages": str(page),
            "Annaul": "",
        }
    )
    r = session.post(LIST_URL, data=data, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def parse_links(html: str, index_url: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for row in soup.select("tr"):
        tds = row.find_all("td")
        if len(tds) != 3:
            continue
        title = tds[1].get_text(strip=True)
        if "英文" not in title:
            continue
        for a in tds[2].find_all("a"):
            href = str(a.get("href", ""))
            ext = Path(unquote(href)).suffix.lower()
            text = a.get_text(strip=True)
            if ext not in ALLOW_EXT:
                continue
            if DROP_RE.search(text):
                continue
            if not KEEP_RE.search(text):
                continue
            url = urljoin(index_url, href)
            out.append((title, url))
            break
    return out


def scrape_ceec_papers(save_dir: Path, limit: int | None = None) -> int:
    sess = requests.Session()
    save_dir.mkdir(parents=True, exist_ok=True)

    seen_urls: set[str] = set()
    count = 0

    for source in SOURCES:
        print(f"Scraping {source['name']}...")
        try:
            first = sess.get(source["index"], timeout=TIMEOUT)
            first.raise_for_status()
            base = hidden_inputs(first.text)

            items: list[tuple[str, str]] = []
            page_idx = 0

            while True:
                html = fetch_page(sess, base, page_idx, source["cat"])
                links = parse_links(html, source["index"])
                new_links = [t for t in links if t[1] not in seen_urls]

                if not new_links:
                    break

                for title, url in new_links:
                    seen_urls.add(url)
                    items.append((title, url))
                page_idx += 1

                if limit and len(items) >= limit:
                    items = items[:limit]
                    break

            for title, url in items:
                tw = re.search(r"(\d{2,3})學年度", title)
                twy = tw.group(1) if tw else "??"
                y = str(int(twy) + 1911) if twy.isdigit() else "????"

                source_type = source["name"]  # GSAT or AST
                if "補考" in title:
                    source_type += "_MAKEUP"

                fname = Path(unquote(url)).name
                # Standard format: YYYY_TWY_TYPE_OriginalName
                save = save_dir / sanitize(f"{y}_{twy}_{source_type}_{fname}")
                if download(sess, url, save):
                    count += 1

            if limit and count >= limit:
                break

        except Exception as e:
            print(f"Error scraping {source['name']}: {e}")

    print("Downloading special files...")
    for item in SPECIAL_FILES:
        try:
            url = str(item["url"])
            twy = str(item["year"])
            y = str(int(twy) + 1911)
            type_str = str(item["type"])

            fname = Path(unquote(url)).name
            save = save_dir / sanitize(f"{y}_{twy}_{type_str}_{fname}")
            if download(sess, url, save):
                count += 1
        except Exception as e:
            print(f"Error downloading {item.get('url', 'unknown')}: {e}")

    return count
