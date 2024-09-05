from urllib.parse import urljoin, urlparse
import os, logging, hashlib, argparse, asyncio, aiohttp
from urllib.robotparser import RobotFileParser
from lxml import html
from rich_argparse import RichHelpFormatter
from collections import defaultdict, deque

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp'}

SIGNATURE = f'''
	███████╗██████╗ ██╗██████╗ ███████╗██████╗ 
	██╔════╝██╔══██╗██║██╔══██╗██╔════╝██╔══██╗
	███████╗██████╔╝██║██║  ██║█████╗  ██████╔╝
	╚════██║██╔═══╝ ██║██║  ██║██╔══╝  ██╔══██╗
	███████║██║     ██║██████╔╝███████╗██║  ██║
	╚══════╝╚═╝     ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝
'''

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

		self.create_folder()

	def create_folder(self):
		try:
			os.makedirs(self.path, exist_ok=True)
		except Exception as e:
			raise SpiderException(f'Failed to create folder: {e}')

	@staticmethod
	async def does_robotstxt_exist(session, url):
		try:
			async with session.head(url) as response:
				return response.status < 400
		except:
			return False

	async def fetch_links_and_image_links(self, session, url):
		if url in self.visited_urls:
			return set()

		self.visited_urls.add(url)
		try:
			async with session.get(url) as response:
				if response.status != 200:
					return set()
				content = await response.text()

			tree = html.fromstring(content)

			links = {urljoin(url, a).lower() for a in tree.xpath('//a/@href')}
			img_urls = {
				urljoin(url, img).lower()
				for img in tree.xpath('//img/@src')
				if os.path.splitext(img)[1][1:].lower() in ALLOWED_IMAGE_EXTENSIONS
			}
			self.img_links.update(img_urls)
			return links
		except Exception as e:
			logging.error(f"Error fetching links from {url}: {e}")
			return set()

	async def download_image(self, session, img_url):
		try:
			parsed_url = urlparse(img_url)
			robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
			self.rp.set_url(robots_url)
			if await self.does_robotstxt_exist(session, robots_url):
				await asyncio.to_thread(self.rp.read)
				if not self.rp.can_fetch("*", img_url):
					logging.warning(f"Robots.txt disallows fetching {img_url}")
					return

			async with session.get(img_url, allow_redirects=True) as response:
				if response.status != 200:
					return
				if 'image' not in response.headers.get('Content-Type', ''):
					logging.warning(f"Content-Type is not an image for {img_url}")
					return
				content = await response.read()

			img_name = hashlib.md5(img_url.encode()).hexdigest() + os.path.splitext(parsed_url.path)[1]
			img_path = os.path.join(self.path, img_name)

			with open(img_path, 'wb') as img_file:
				img_file.write(content)
				logging.info(f'Downloaded {img_url}')
		except Exception as e:
			logging.error(f'Failed to download {img_url}: {e}')

	async def download(self):
		async with aiohttp.ClientSession(headers={'User-Agent': 'spider/1.0'}) as session:
			queue = deque([(0, url) for url in self.ALL_LINKS[0]])
			while queue:
				depth, url = queue.popleft()
				if depth > self.depth:
					continue

				new_links = await self.fetch_links_and_image_links(session, url)
				if depth < self.depth and self.recr:
					for link in new_links:
						if link not in self.visited_urls:
							queue.append((depth + 1, link))
							self.ALL_LINKS[depth + 1].add(link)

			tasks = [self.download_image(session, url) for url in self.img_links]
			await asyncio.gather(*tasks)

		logging.info(f"Total image links found: {len(self.img_links)}")
		logging.info(f"Total images downloaded: {len([f for f in os.listdir(self.path) if os.path.isfile(os.path.join(self.path, f))])}")

class ArgParser:
	def check_positive(self, value):
		ivalue = int(value)
		if ivalue < 0:
			raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
		return ivalue

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
			type=self.check_positive,
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

async def main():
	args = ArgParser().parse_args()
	try:
		s = Spider(args.recursive, args.level, args.URL, args.path)
		await s.download()
	except Exception as e:
		logging.error(f"Error occurred: {e}")

if __name__ == '__main__':
	asyncio.run(main())