import argparse
import requests
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import logging
from urllib.robotparser import RobotFileParser
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from rich_argparse import RichHelpFormatter
import hashlib
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp'}

class SpiderException(Exception):
	pass

class Spider:
	def __init__(self, recr, depth, url, path):
		self.depth = depth if recr else 0
		self.path = path
		self.ALL_LINKS = defaultdict(set)
		self.ALL_LINKS[0].add(url)
		self.img_links = set()
		self.recr = recr
		self.visited_urls = set()
		self.rp = RobotFileParser()
		self.session = requests.Session()
		self.session.headers.update({'User-Agent': 'YourBot/1.0'})

		try:
			chrome_options = Options()
			chrome_options.add_argument("--headless")
			self.driver = webdriver.Chrome(service=Service('/Users/tpetros/homebrew/bin/chromedriver'), options=chrome_options)
			self.create_folder()
		except Exception as e:
			raise SpiderException(f'{e}')

	def create_folder(self):
		try:
			os.makedirs(self.path, exist_ok=True)
		except Exception as e:
			raise SpiderException(f'{e}')

	def fetch_links_and_image_links(self, url):
		if url in self.visited_urls:
			return set()

		self.visited_urls.add(url)
		try:
			self.driver.get(url)
			self.driver.implicitly_wait(2)

			# Fetch links
			links = self.driver.find_elements(By.TAG_NAME, 'a')
			urls = {urljoin(url, link.get_attribute('href')) for link in links if link.get_attribute('href')}

			# Fetch image links
			img_tags = self.driver.find_elements(By.TAG_NAME, 'img')
			img_urls = {
				urljoin(url, img.get_attribute('src'))
				for img in img_tags
				if img.get_attribute('src') and os.path.splitext(img.get_attribute('src'))[1][1:].lower() in ALLOWED_IMAGE_EXTENSIONS
			}
			self.img_links.update(img_urls)
			return urls
		except Exception as e:
			logging.error(f"Error fetching links from {url}: {e}")
			return set()

	def download_image(self, img_url):
		try:
			parsed_url = urlparse(img_url)
			self.rp.set_url(f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt")
			self.rp.read()
			if not self.rp.can_fetch("*", img_url):
				logging.warning(f"Robots.txt disallows fetching {img_url}")
				return

			response = self.session.get(img_url, timeout=10, allow_redirects=True)
			response.raise_for_status()

			if 'image' not in response.headers.get('Content-Type', ''):
				logging.warning(f"Content-Type is not an image for {img_url}")
				return

			img_name = hashlib.md5(img_url.encode()).hexdigest() + os.path.splitext(parsed_url.path)[1]
			img_path = os.path.join(self.path, img_name)

			with open(img_path, 'wb') as img_file:
				img_file.write(response.content)
				logging.info(f'Downloaded {img_url}')
		except requests.exceptions.RequestException as e:
			logging.warning(f"Failed to fetch {img_url}: {e}")
		except Exception as e:
			logging.error(f'Failed to download {img_url}: {e}')

	def download(self):
		i = 0
		with ThreadPoolExecutor(max_workers=10) as executor:
			while i <= self.depth:
				new_links = set()
				futures = {executor.submit(self.fetch_links_and_image_links, url): url for url in self.ALL_LINKS[i]}
				for future in as_completed(futures):
					try:
						result = future.result()
						new_links.update(result)
						if not self.recr:
							break
					except Exception as e:
						logging.error(f"Error fetching links: {e}")
				self.ALL_LINKS[i + 1] = new_links - self.visited_urls
				i += 1

			image_futures = [executor.submit(self.download_image, url) for url in self.img_links]
			for future in as_completed(image_futures):
				try:
					future.result()
				except Exception as e:
					logging.error(f"Error downloading images: {e}")

		logging.info(f"Total image links found: {len(self.img_links)}")
		logging.info(f"Total images downloaded: {len([f for f in os.listdir(self.path) if os.path.isfile(os.path.join(self.path, f))])}")

class ArgParser:
	def __init__(self):
		self.parser = argparse.ArgumentParser(
			description="A tool to download images from a URL with optional recursive depth.",
			formatter_class=RichHelpFormatter
		)
		self.parser.add_argument(
			'-r', '--recursive',
			action='store_true',
			help="Recursively downloads the images in the specified URL."
		)
		self.parser.add_argument(
			'-l', '--level',
			type=int,
			default=5,
			help="Maximum depth level for recursive download. Default is 5."
		)
		self.parser.add_argument(
			'-p', '--path',
			type=str,
			default='./data/',
			help="Path to save the downloaded files. Default is './data/'."
		)
		self.parser.add_argument(
			'URL',
			type=str,
			help="The URL to start downloading from."
		)

	def parse_args(self):
		return self.parser.parse_args()

def main():
	args = ArgParser().parse_args()
	try:
		s = Spider(args.recursive, args.level, args.URL, args.path)
		s.download()
	except Exception as e:
		logging.error(f"Error occurred: {e}")


if __name__ == '__main__':
	main()
