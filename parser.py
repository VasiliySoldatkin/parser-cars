from bs4 import BeautifulSoup
import requests
import os
import io

class AutoParser:
    def __init__(self):
        self.class_ = 'ListingItem-module__main'
        self.class_desc = 'ListingItem-module__description'
        self.class_car_name = 'Link ListingItemTitle__link'  # IndexMarks__item-name
        self.mark_cars_info = {}
        self.class_next_page = 'Button Button_color_white Button_size_s Button_type_link Button_width_default ListingPagination-module__next'
        self.class_pagination = 'ListingPagination-module__sequenceControls'
        self.session = requests.Session()
        headers = {'User-Agent': 'GoogleBot',
                   'Content-Type': 'text/html',
                   'Accept': "text/html"}
        self.session.headers.update(headers)
        self.amount_img = 0

    def download_images(self, limit=1):
        cars = self.parse_car(limit)
        print(self.amount_img)
        print('Загрузить изображения '
              'в каталог '
              f'\n{os.getcwd()} ?')
        if input() == 'да':
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
                            out = io.open(os.path.join(download_folder, car + f'({count})')+'.jpg', "wb")
                            out.write(p.content)
                            out.close()
                            count += 1
        return False


    def find_marks(self):
        class_ = 'IndexMarks__item'
        url = 'https://auto.ru/'
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, 'lxml')
        marks = soup.find_all('a', class_=class_)
        return marks

    def load_body(self, url):
        response = self.session.get(url)
        response.encoding = 'utf-8'
        body = response.text
        soup = BeautifulSoup(body, 'lxml')
        return body, soup

    def find_images(self, soup):
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
                self.mark_cars_info[car_name].append('http:' + img['src'])
                self.amount_img += 1

    @staticmethod
    def get_next_page(control):
        return control['rel'][0] == 'next'

    @staticmethod
    def is_empty(item):
        return len(item) == 0

    def parse_car(self, limit=1):
        marks = self.find_marks()
        cars = []
        for mark in marks[:limit]:
            self.mark_cars_info = {}
            count = 0
            next = [mark]
            mark_name = mark.find('div', class_='IndexMarks__item-name').text
            while not self.is_empty(next):
                page = next[0]
                body, soup = self.load_body(page['href'])
                print(page['href'])
                self.find_images(soup)
                pagination_controls = soup.find('div', class_=self.class_pagination)
                pag_prev_next = pagination_controls.find_all('link')
                next = list(filter(self.get_next_page, pag_prev_next))
                count += 1
                print(count)
            cars.append([mark_name, self.mark_cars_info])
        return cars

parser = AutoParser()
parser.download_images(5)
