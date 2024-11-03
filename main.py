import requests
import os
import json
from pprint import pprint
from tqdm import tqdm
import datetime

TOKEN_VK = '...'
USER_ID = 62268022
YA_DISK_TOKEN = '...'
NUM_PHOTOS = 5
DOWNLOAD_FOLDER = 'VK_photos'
RESULT_JSON = 'uploaded_photos.json'


class VKAPIClient:
    API_BASE_URL = 'https://api.vk.com/method'

    def __init__(self, token, user_id):
        self.token = token
        self.user_id = user_id

    def get_common_params(self):
        return {
            'access_token': self.token,
            'v': '5.131'
        }

    def get_profile_photos(self):
        params = self.get_common_params()
        params.update({
            'owner_id': self.user_id,
            'album_id': 'profile',
            'photo_sizes': 1,
            'count': NUM_PHOTOS,
            'extended': 1
        })
        response = requests.get(f'{self.API_BASE_URL}/photos.get', params=params)

        return response.json()

class YandexDisk:
    BASE_URL = 'https://cloud-api.yandex.net/v1/disk/resources'

    def __init__(self, token):
        self.token = token

    def create_folder(self, path):
        headers = {'Authorization': f'OAuth {self.token}'}
        response = requests.put(f'{self.BASE_URL}?path={path}&overwrite=true', headers=headers)
        if response.status_code == 201:
            print(f'Папка {path} создана.')
        elif response.status_code == 409:
            print(f'Папка {path} уже существует.')
        else:
            print('Ошибка при создании папки:', response.json())

    def upload_file(self, file_path, ya_path):
        headers = {'Authorization': f'OAuth {self.token}'}
        upload_url = requests.get(f'{self.BASE_URL}/upload?path={ya_path}&overwrite=true', headers=headers).json().get('href')
        with open(file_path, 'rb') as f:
            response = requests.put(upload_url, files={'file': f})
        return response.status_code == 201

def download_photos_to_yadisk(photos, folder_name, ya_disk):
    yandex_path = folder_name + '/'
    ya_disk.create_folder(yandex_path)
    uploaded_files_info = []
    seen_likes = {}

    for photo in tqdm(photos, desc='Загрузка фотографий'):
        max_size = max(photo['sizes'], key=lambda x: x['width'] * x['height'])
        file_url = max_size['url']
        likes_count = photo.get('likes', {}).get('count', 0)

        if likes_count not in seen_likes:
            file_name = f"{likes_count}.jpg"
        else:
            date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{likes_count}_{date_str}.jpg"

        seen_likes[likes_count] = file_name

        print(f"Обработка фотографии: {file_name}, URL: {file_url}, Likes: {likes_count}")

        img_response = requests.get(file_url)
        if img_response.status_code == 200:
            local_file_path = os.path.join(DOWNLOAD_FOLDER, file_name)
            with open(local_file_path, 'wb') as f:
                f.write(img_response.content)
            print(f'Успешно загружено: {file_name}')

            if ya_disk.upload_file(local_file_path, yandex_path + file_name):
                print(f'Файл {file_name} загружен на Я.Диск.')
                uploaded_files_info.append({'file_name': file_name, 'size': max_size['type']})
            else:
                print(f'Ошибка при загрузке {file_name} на Я.Диск.')

            os.remove(local_file_path)
        else:
            print(f'Ошибка загрузки {file_name}: {img_response.status_code}')

    with open(RESULT_JSON, 'w', encoding='utf-8') as json_file:
        json.dump(uploaded_files_info, json_file, ensure_ascii=False, indent=4)
    print(f'Информация о загруженных фотографиях сохранена в {RESULT_JSON}.')

def main():
    vk_client = VKAPIClient(TOKEN_VK, USER_ID)
    photos_info = vk_client.get_profile_photos()

    if 'response' in photos_info and 'items' in photos_info['response']:
        photos = photos_info['response']['items']
        download_photos_to_yadisk(photos, DOWNLOAD_FOLDER, YandexDisk(YA_DISK_TOKEN))
    else:
        print('Не удалось получить фото. Проверьте настройки конфиденциальности или корректность токена/ID пользователя.')

if __name__ == '__main__':
    main()