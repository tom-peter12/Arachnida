import re
import time
import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

def append_http(url):
	if not url.startswith(('http://', 'https://')):
		return 'http://' + url
	return url

class Spider:
	def __init__(self, depth, url, path):
		self.depth = depth
		self.path = path
		self.url = url

	def fetch_links(self, url):
		try:
			response = requests.get(url)
			soup = BeautifulSoup(response.text, 'html.parser')
			links = soup.find_all('a')
			urls = [urljoin(url, link.get('href')) for link in links if link.get('href')]
			return urls
		except Exception as e:
			print(f"Error processing {url}: {e}")
			return []

	def fetch_images(self, url):
		try:
			response = requests.get(url)
			soup = BeautifulSoup(response.text, 'html.parser')
			img_tags = soup.find_all('img')
			img_urls = [urljoin(url, img['src']) for img in img_tags if img.get('src')]
			return img_urls
		except Exception as e:
			print(f"Error fetching images from {url}: {e}")
			return []

	def download_image(self, img_url):
		try:
			img_data = requests.get(img_url).content
			img_name = os.path.join(self.path, os.path.basename(urlparse(img_url).path))
			with open(img_name, 'wb') as img_file:
				img_file.write(img_data)
			print(f'Downloaded {img_url}')
		except Exception as e:
			print(f'Failed to download {img_url}: {e}')

	def download(self):
		ALL_LINKS = {
			0: [self.url],
		}
		os.makedirs(self.path, exist_ok=True)

		with ThreadPoolExecutor(max_workers=10) as executor:
			for i in range(self.depth):
				new_links = []
				futures = {executor.submit(self.fetch_links, url): url for url in ALL_LINKS[i]}
				for future in as_completed(futures):
					try:
						result = future.result()
						new_links.extend(result)
					except Exception as e:
						print(f"Error fetching links: {e}")
				ALL_LINKS[i + 1] = new_links

			image_futures = []
			for level in range(self.depth + 1):
				for url in ALL_LINKS.get(level, []):
					image_futures.append(executor.submit(self.fetch_images, url))

			for future in as_completed(image_futures):
				try:
					img_urls = future.result()
					for img_url in img_urls:
						executor.submit(self.download_image, img_url)
				except Exception as e:
					print(f"Error processing images: {e}")

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('-r', '--recursive', action='store_true', help="recursively downloads the images in a URL received as a parameter")
	parser.add_argument('-l', '--level', type=int, default=5, help="indicates the maximum depth level of the recursive download. If not indicated, it will be 5")
	parser.add_argument('-p', '--path', type=str, default='./data/', help="indicates the path where the downloaded files will be saved. If not specified, ./data/ will be used")
	parser.add_argument('url', help="the URL to start downloading from")

	args = parser.parse_args()

	s = Spider(args.level, args.url, args.path)
	s.download()
