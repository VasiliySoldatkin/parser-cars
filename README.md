# Scraper-cars
## Установка зависимостей:
```pip install -r requirements.txt```  
## Пример:
```python
import scraping.scrape_marks as sm
s = sm.AutoScraper('config.ini')
s.output()
```
## Логика скрипта
1) Метод __download_images__ создает в текущей папки каталоги с названием моделей машин, в которые загружаются фотографии марок этих машин.
2) Метод __download_to_csv__ создает csv файл с ссылками на изображения марок машин, т.е. csv файл имеет столбы img_url, mark, model.
3) Метод __output__ запускает загрузку изображения в зависимости от выставленного режима в конфиге.
4) Метод __find_marks__ находит все марки машин с главного сайта.
5) Метод __load_body__ загружает тело сайта.
6) Метод __find_images__ находит все изображения конкретной марки (т.е. изображения моделей) и возвращает словарь, в котором ключами являются модели машин, а значениями списки из ссылок на изображения этих моделей.
7) Метод __parse_car__ считывает конфиг, исключает марки машин, осуществляет проход пагинации по кнопкам перехода и после формирует двумерный список с названием марки и информацией о ней.
### Порядок выполнения
Сначала инициализируется экземпляр класса __AutoParser__, потом создается запускается метод __output__, который запускает основной метод __parse_car__.  
В __parse_car__ считывается конфиг и запускается метод __find_marks__. После получения марок машин считывается файл __marks.txt__, если это прописано в конфиге.  
Формируется список марок __marks_to_pars__ (может стоять как из марок машин из файла __marks.txt__, так и с сайта). Аналогично с моделями машин.
Далее в цикле для каждой марки машины скачиваются изображения их моделей. Для этого парсер проходит пагинацию с помощью кнопок перехода на следующую страницу, пока кнопка перехода не перестанет быть активной. 