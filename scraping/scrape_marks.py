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
        self.class_ = 'ListingItem-module__main'
        self.class_desc = 'ListingItem-module__description'
        self.class_car_name = 'Link ListingItemTitle__link'  # IndexMarks__item-name
        self.mark_cars_info = {}
        self.cars = []
        self.class_next_page = 'Button Button_color_white Button_size_s Button_type_link Button_width_default ListingPagination-module__next'
        self.class_pagination = 'ListingPagination-module__sequenceControls'
        self.amount_img = 0
        self.path = path
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=100))
        headers = {'User-Agent': 'GoogleBot',
                   'Content-Type': 'text/html',
                   'Accept': "text/html"}
        self.session.headers.update(headers)
        self.models_to_pars = {}
        self.marks_to_pars = {}
        self.exclude_model = False
        self.exclude_mark = False
        self.config = configparser.ConfigParser()
        self.config.read(self.path, encoding='utf-8')

    @staticmethod
    def download_images(cars):
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

    def run(self):
        self.t = time.time()
        self.start_parser()
        print("Асинхронность: ", time.time() - self.t)
        output_mode = self.config['OutputMode']['output_mode']
        if output_mode == 'image':
            self.download_images(self.cars)
        elif output_mode == 'csv':
            self.download_to_csv(self.cars)
        else:
            print('Wrong Output Mode')

    async def gather_with_concurrency(self, n, *tasks):
        semaphore = asyncio.Semaphore(n)

        async def sem_task(task):
            async with semaphore:
                return await task

        return await asyncio.gather(*(sem_task(task) for task in tasks))

    def find_marks(self):
        class_ = 'IndexMarks__item'
        url = 'https://auto.ru/'
        response = requests.Session().get(url)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')
        marks = soup.find_all('a', class_=class_)
        return marks

    async def find_images(self, soup):
        cars = soup.find_all('div', class_=self.class_)
        t = time.time()
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
        print(time.time() - t)

    @staticmethod
    def get_next_page(control):
        return control['rel'][0] == 'next'

    async def pages_list(self, mark, session):
        next = [mark]
        soups = []
        while not self.is_empty(next):
            page = next[0]
            t = time.time()
            async with session.get(page['href']) as response:
                body = await response.text(encoding='utf-8')
                soup = BeautifulSoup(body, 'lxml')
                pagination_controls = soup.find('div', class_=self.class_pagination)
                try:
                    pag_prev_next = pagination_controls.find_all('link')
                except:
                    continue
                else:
                    next = list(filter(self.get_next_page, pag_prev_next))
                soups.append(soup)
            print('This: ', time.time() - t)

        return soups
    @staticmethod
    def is_empty(item):
        return len(item) == 0


    def start_parser(self):
        t = time.time()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.parse_car())
        print(f'Время: {time.time() - t}')


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

        async with self.session as session:
            for mark in marks:
                self.mark_cars_info = {}
                mark_name = mark.find('div', class_='IndexMarks__item-name').text
                if mark_name not in self.marks_to_pars and self.exclude_mark:
                    continue
                print(mark_name)
                soups = await self.pages_list(mark, session)
                tasks = [asyncio.create_task(self.find_images(soup)) async for soup in soups]
                await asyncio.gather(*tasks)
                self.cars.append([mark_name, self.mark_cars_info])
