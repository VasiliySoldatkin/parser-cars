import sys
import time

from bs4 import BeautifulSoup
import requests
import os
import io
import pandas as pd
import configparser
import asyncio
import aiohttp


class AutoScraper:

    def __init__(self, path):
        self.t = 0
        self.workers = 100
        self.class_ = 'ListingItem-module__main'
        self.class_desc = 'ListingItem-module__description'
        self.class_car_name = 'Link ListingItemTitle__link'  # IndexMarks__item-name
        self.mark_cars_info = {}
        self.cars = []
        self.class_next_page = 'Button Button_color_white Button_size_s Button_type_link ' \
                               'Button_width_default ListingPagination-module__next'
        self.class_pagination = 'ControlGroup ControlGroup_responsive_no ControlGroup_size_s ' \
                                'ListingPagination-module__pages'
        self.class_pagination_a = 'Button Button_color_whiteHoverBlue Button_size_s Button_type_link ' \
                                  'Button_width_default ListingPagination-module__page'
        self.amount_img = 0
        self.path = path
        self.models_to_pars = {}
        self.marks_to_pars = {}
        self.exclude_model = False
        self.exclude_mark = False
        self.config = configparser.ConfigParser()
        self.config.read(self.path, encoding='utf-8')

        self.p = 0

    def run(self):
        self.t = time.time()
        self.start_parser()
        output_mode = self.config['OutputMode']['output_mode']
        if output_mode == 'image':
            self.download_images(self.cars)
        elif output_mode == 'csv':
            self.download_to_csv(self.cars)
        else:
            print('Wrong Output Mode')

    def start_parser(self):
        t = time.time()
        if sys.platform == 'win32':
            loop = asyncio.ProactorEventLoop()
        else:
            import selectors
            loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.parse_car())
        t = time.time() - t
        print(f'Время: {t}')

    async def parse_car(self):
        marks_file = self.config['Marks']['marks_file']
        models_file = self.config['Models']['models_file']
        marks = self.find_marks()

        if marks_file != '*':
            self.exclude_mark = True
            with open(marks_file, 'r', encoding='utf-8') as f:
                self.marks_to_pars = set(f.read().split('\n'))
        else:
            self.marks_to_pars = set(map(lambda mark: mark.find('div', class_='IndexMarks__item-name').text, marks))

        if models_file != '*':
            self.exclude_model = True
            with open(models_file, 'r') as f:
                self.models_to_pars = set(f.read().split('\n'))
        timeout = aiohttp.ClientTimeout(total=None)
        session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=30), timeout=timeout)
        headers = {'User-Agent': 'GoogleBot',
                   'Content-Type': 'text/html',
                   'Accept': "text/html"}
        session.headers.update(headers)
        async with session:
            for mark in marks:
                self.mark_cars_info = {}
                mark_name = mark.find('div', class_='IndexMarks__item-name').text
                if mark_name not in self.marks_to_pars and self.exclude_mark:
                    continue
                print(mark_name)
                params = self.pages_list(mark, session)
                tasks = [asyncio.create_task(self.find_images(mark['href'], param, session)) async for param in params]
                return_tasks = await self.gather_with_concurrency(self.workers, *tasks)
                while len(return_tasks) != 0:
                    tasks = [asyncio.create_task(self.find_images(param['url'], param['params'], param['session']))
                             for param in return_tasks if param is not None]
                    return_tasks = await self.gather_with_concurrency(self.workers, *tasks)

                self.cars.append([mark_name, self.mark_cars_info])
                self.p = 0

    async def find_images(self, url, params, session):
        try:
            async with session.get(url, params=params, timeout=40, ssl=False) as response:
                soup = BeautifulSoup(await response.text(encoding='utf-8'), 'lxml')
                cars = soup.find_all('div', class_=self.class_)
                for car in cars:
                    car_name = car.find('div', class_=self.class_desc).find('a', class_=self.class_car_name).text
                    if car_name not in self.mark_cars_info.keys():
                        self.mark_cars_info[car_name] = []
                    car_imgs = car.find_all('img')
                    for img in car_imgs:
                        if img['class'] == 'OfferPanorama__previewLayer OfferPanorama__previewLayer_2':
                            continue
                        if img['src'].startswith('data:'):
                            continue
                        if car_name not in self.models_to_pars and self.exclude_model:
                            continue
                        self.mark_cars_info[car_name].append('http:' + img['src'])
                        self.amount_img += 1
            page = params['page']
            print(f'Page: {page}')
            return
        except asyncio.TimeoutError:
            return {'url': url, 'params': params, 'session': session}

    async def pages_list(self, mark, session):
        first_page = mark
        response = await session.get(first_page['href'])
        body = await response.text(encoding='utf-8')
        soup = BeautifulSoup(body, 'lxml')
        pages = soup.find('span', class_=self.class_pagination).find_all('a', class_=self.class_pagination_a)
        max_page = pages[-1].find('span', class_='Button__text').text
        for page_num in range(int(max_page)+1):
            page = {'page': page_num}
            yield page

    @staticmethod
    def download_images(cars):
        if not os.path.isdir('output'):
            os.mkdir('output')
        os.chdir(os.path.join(os.getcwd(), 'output'))
        for mark, cars_info in cars:
            print(mark)
            if not os.path.isdir(mark):
                os.mkdir(mark)
            print(os.path.join(os.getcwd(), mark))
            download_folder = os.path.join(os.getcwd(), mark)
            for car in cars_info:
                count = 1
                if len(cars_info[car]) != 0:
                    for img in cars_info[car]:
                        p = requests.get(img)
                        out = io.open(os.path.join(download_folder, car + f'({count})') + '.jpg', "wb")
                        out.write(p.content)
                        out.close()
                        count += 1

    def download_to_csv(self, cars):
        df = pd.DataFrame({'img_url': [], 'mark': [], 'model': []})
        for mark, cars_info in cars:
            for model in cars_info:
                for img in cars_info[model]:
                    df = df.append({'img_url': img, 'mark': mark, 'model': model}, ignore_index=True)
        csv_file = self.config['OutputMode']['csv_output']
        if csv_file.endswith('.csv'):
            df.to_csv(self.config['OutputMode']['csv_output'], sep='\t', encoding='utf-8')
        else:
            print('Wrong file format')

    @staticmethod
    async def gather_with_concurrency(n, *tasks):
        semaphore = asyncio.Semaphore(n)

        async def sem_task(task):
            async with semaphore:
                return await task

        tasks = [sem_task(task) for task in tasks]
        return await asyncio.gather(*tasks)

    @staticmethod
    def find_marks():
        class_ = 'IndexMarks__item'
        url = 'https://auto.ru/'
        response = requests.Session().get(url)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')
        marks = soup.find_all('a', class_=class_)
        return marks