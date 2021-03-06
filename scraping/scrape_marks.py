import time

from bs4 import BeautifulSoup
import requests
import os
import io
import pandas as pd
import configparser

class AutoScraper:
    def __init__(self, path):
        self.class_ = 'ListingItem-module__main'
        self.class_desc = 'ListingItem-module__description'
        self.class_car_name = 'Link ListingItemTitle__link'  # IndexMarks__item-name
        self.mark_cars_info = {}
        self.class_next_page = 'Button Button_color_white Button_size_s Button_type_link Button_width_default ListingPagination-module__next'
        self.class_pagination = 'ControlGroup ControlGroup_responsive_no ControlGroup_size_s ListingPagination-module__pages'
        self.class_pagination_a = 'Button Button_color_whiteHoverBlue Button_size_s Button_type_link Button_width_default ListingPagination-module__page'
        self.amount_img = 0
        self.path = path
        self.session = requests.Session()
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
        csv_path = self.config['OutputMode']['csv_output']
        path = csv_path.split('/')
        if not path[-1].endswith('.csv'):
            print('Wrong file format')
            return
        df = pd.DataFrame({'img_url': [], 'mark': [], 'model': []})
        for mark, cars_info in cars:
            for model in cars_info:
                for img in cars_info[model]:
                    df = df.append({'img_url': img, 'mark': mark, 'model': model}, ignore_index=True)
        df.to_csv(csv_path, sep='\t', encoding='utf-8')

    def output(self):
        t = time.time()
        cars = self.parse_car()
        output_mode = self.config['OutputMode']['output_mode']
        if output_mode == 'image':
            self.download_images(cars)
        elif output_mode == 'csv':
            self.download_to_csv(cars)
        else:
            raise FileNotFoundError('???????????????? ???????????? ??????????')
        print(time.time() - t)

    def find_marks(self):
        class_ = 'IndexMarks__item'
        url = 'https://auto.ru/'
        response = self.session.get(url)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')
        marks = soup.find_all('a', class_=class_)
        return marks

    def load_body(self, url):
        response = self.session.get(url)
        response.encoding = 'utf-8'
        body = response.text
        soup = BeautifulSoup(body, 'lxml')
        return body, soup

    def find_images(self, url):

        response = self.session.get(url)
        response.encoding = 'utf-8'
        body = response.text
        soup = BeautifulSoup(body, 'lxml')
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
        print(self.amount_img)
    @staticmethod
    def get_next_page(control):
        return control['rel'][0] == 'next'

    @staticmethod
    def is_empty(item):
        return len(item) == 0

    def parse_car(self):

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
        cars = []
        for mark in marks:
            self.mark_cars_info = {}
            mark_name = mark.find('div', class_='IndexMarks__item-name').text
            if mark_name not in self.marks_to_pars and self.exclude_mark:
                continue
            print(mark_name)
            next = [mark]
            first_page = next[0]
            body, soup = self.load_body(first_page['href'])
            max_page = soup.find('span', class_=self.class_pagination).find_all('a', class_=self.class_pagination_a)[-1].find('span', class_='Button__text').text
            for page_num in range(int(max_page) + 1):
                page = first_page['href'] + f'?page={page_num}'
                print('Page: ', page_num)
                self.find_images(page)
            cars.append([mark_name, self.mark_cars_info])
        return cars

