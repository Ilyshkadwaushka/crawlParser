import urllib.request
from urllib.parse import urlparse, urljoin
import urllib.error
from html.parser import HTMLParser
import threading
import time
import logging
from typing import List, AnyStr
import csv

logging.basicConfig(level=logging.INFO)

class LinkParser(HTMLParser):
    """Парсер HTML-кода страницы для извлечения ссылок"""
    def __init__(self, base_url: AnyStr, page_url: AnyStr) -> None:
        super().__init__()
        self.base_url = base_url
        self.page_url = page_url
        self.links = []

    def handle_starttag(self, tag: AnyStr, attrs: list[tuple[str, str | None]]) -> None:
        if tag == 'a':
            for (attribute, value) in attrs:
                if attribute == 'href':
                    url = urljoin(self.base_url, value)
                    if url.startswith(self.base_url):
                        self.links.append(url)

class SiteMapBuilder:
    """Построитель карты сайта"""
    def __init__(self, url: AnyStr, max_depth=3) -> None:
        self.base_url = urlparse(url).scheme + '://' + urlparse(url).hostname
        self.url = url
        self.max_depth = max_depth
        self.pages = set()
        self.lock = threading.Lock()

    def add_page(self, url: AnyStr, depth: int) -> bool:
        """Добавление страницы в список обработанных"""
        with self.lock:
            if url not in self.pages and depth <= self.max_depth:
                self.pages.add(url)
                return True
            return False

    def get_links(self, url: AnyStr) -> List:
        """Получение списка ссылок на странице"""
        try:
            response = urllib.request.urlopen(url, timeout=5)
            if response.getheader('Content-Type').startswith('text/html'):
                parser = LinkParser(self.base_url, url)
                parser.feed(response.read().decode())
                return parser.links
            response.close()
            return []
        except:
            return []

    def crawl(self, url: AnyStr, depth: int) -> None:
        """Рекурсивный обход страниц"""
        if depth > self.max_depth:
            return

        if not self.add_page(url, depth):
            return

        logging.info(f"Crawling: {url}")

        links = self.get_links(url)
        for link in links:
            t = threading.Thread(target=self.crawl, args=(link, depth+1))
            t.daemon = True
            t.start()

    def build(self) -> None:
        """Запуск построения карты"""
        start_time = time.time()
        self.crawl(self.url, 1)
        end_time = time.time()

        # Сохранение карты в файл
        parsed_url = urlparse(self.url)
        filename = parsed_url.netloc + '.txt'
        with open('data/'+filename, 'w') as f:
            for page in self.pages:
                f.write(page + '\n')

        data = [[self.url, f"{end_time-start_time:.{2}f}", len(self.pages), filename]]
        fieldnames = ['URL сайта', 'Время обработки', 'Кол-во найденных ссылок', 'Имя файла с результатом']
        with open('data/summary.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            if csvfile.tell() == 0:
                writer.writerow(fieldnames)
            for row in data:
                writer.writerow(row)

        logging.info(f"Site map for {self.url} built in {end_time - start_time} seconds\n"
                     f"Number of pages: {self.pages.__len__()}\n"
                     f"Saved to {filename}")

if __name__ == '__main__':
    urls = [
        'http://crawler-test.com/',
        'http://google.com/',
        'https://vk.com',
        'https://dzen.ru',
        'https://stackoverflow.com',
    ]
    result = [SiteMapBuilder(i).build() for i in urls]
