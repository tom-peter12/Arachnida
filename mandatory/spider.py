from urllib.parse import urljoin, urlparse
import os, logging, hashlib, argparse, asyncio, aiohttp, datetime
from urllib.robotparser import RobotFileParser
from lxml import html
from rich_argparse import RichHelpFormatter
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Pool

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
		self.img_links = []
		self.recr = recr
		self.visited_urls = set()
		self.rp = RobotFileParser()

		self.create_folder()
		self.executor = ThreadPoolExecutor(max_workers=10)
		self.pool = Pool(processes=10)

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

	async def fetch_with_redirect_loop_detection(self, session, url):
		visited_urls = set()
		max_redirects = 5

		for _ in range(max_redirects):
			if url in visited_urls:
				logging.error(f"Circular redirect detected: {url}")
				return None
			visited_urls.add(url)

			async with session.get(url, allow_redirects=False) as response:
				if 300 <= response.status < 400:
					new_url = response.headers.get('Location')
					if new_url is None:
						logging.error(f"Redirect with no 'Location' header from {url}")
						return None
					url = urljoin(url, new_url)
					logging.info(f"Redirecting to {new_url}")
				else:
					return await response.text()

		logging.error(f"Too many redirects for {url}")
		return None

	async def fetch_links(self, session, url):
		if url in self.visited_urls:
			return set()

		self.visited_urls.add(url)
		try:
			content = await self.fetch_with_redirect_loop_detection(session, url)
			if content is None:
				return set()

			tree = html.fromstring(content)

			links = {urljoin(url, a).lower() for a in tree.xpath('//a/@href')}
			img_urls = [
				urljoin(url, img).lower()
				for img in tree.xpath('//img/@src')
				if os.path.splitext(img)[1][1:].lower() in ALLOWED_IMAGE_EXTENSIONS
			]
			self.img_links.extend(img_urls)
			logging.info(f"Found {len(img_urls)} images on {url}")
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
					logging.warning(f"Failed to download {img_url}: Status {response.status}")
					return
				if 'image' not in response.headers.get('Content-Type', ''):
					logging.warning(f"Content-Type is not an image for {img_url}")
					return
				content = await response.read()

			img_name = await asyncio.get_event_loop().run_in_executor(self.executor, lambda: hashlib.md5(img_url.encode() + str(datetime.datetime.now()).encode()).hexdigest())
			img_path = os.path.join(self.path, img_name + os.path.splitext(parsed_url.path)[1])

			with open(img_path, 'wb') as img_file:
				img_file.write(content)
				logging.info(f'Downloaded {img_url}')
		except Exception as e:
			logging.error(f'Failed to download {img_url}: {e}')

	async def process_url(self, session, url):
		new_links = await self.fetch_links(session, url)
		for link in new_links:
			if link not in self.visited_urls:
				if self.recr and (len(self.ALL_LINKS) <= self.depth):
					self.ALL_LINKS[len(self.ALL_LINKS)].add(link)

	async def download(self):
		timeout = aiohttp.ClientTimeout(total=60)
		async with aiohttp.ClientSession(headers={'User-Agent': 'spider/1.0'}, timeout=timeout) as session:
			queue = deque([(0, url) for url in self.ALL_LINKS[0]])
			image_tasks = set()

			while queue:
				depth, url = queue.popleft()
				if depth > self.depth:
					continue

				await self.process_url(session, url)

				for img_url in self.img_links:
					image_tasks.add(asyncio.create_task(self.download_image(session, img_url)))

				if depth < self.depth and self.recr:
					for link in self.ALL_LINKS[depth + 1]:
						if link not in self.visited_urls:
							queue.append((depth + 1, link))

			self.pool.map(lambda img_url: asyncio.run(self.download_image(session, img_url)), self.img_links)
			await asyncio.gather(*image_tasks)

		logging.info(f"Total image links found: {len(self.img_links)}")
		logging.info(f"Total images downloaded: {len([f for f in os.listdir(self.path) if os.path.isfile(os.path.join(self.path, f))])}")

class ArgParser:
	def check_positive(self, value):
		ivalue = int(value)
		if ivalue <= 0:
			raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
		return ivalue
	
	def validate_and_confirm(self, args):
		print("\n" + "="*50)
		print("📋 **Please Confirm Your Settings Before Starting the Download**")
		print("="*50)
		
		print(f"🔄 **Recursive**: {'Yes' if args.recursive else 'No'}")
		print(f"📊 **Level**: {args.level} (default)" if args.level == 5 else f"📊 **Level**: {args.level}")
		print(f"📂 **Path**: {args.path} (default)" if args.path == './data/' else f"📂 **Path**: {args.path}")
		print(f"🌐 **URL**: {args.URL}")
		
		print("="*50)
		while True:
			confirmation = input("✅ Is the above information correct? (yes/no): ").strip().lower()
			if confirmation == 'yes':
				print("\n✔️ **Confirmation Received. Starting Download...**\n")
				return True
			elif confirmation == 'no':
				return False
			else:
				print("\n❌ **Invalid input. Please provide a valid input.**\n")

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
		args = self.parser.parse_args()
		if self.validate_and_confirm(args):
			return args
		else:
			raise SystemExit("\n❌ **Operation Cancelled. Please provide the correct information and try again.**\n")

async def main():
	args = ArgParser().parse_args()
	try:
		s = Spider(args.recursive, args.level, args.URL, args.path)
		await s.download()
	except Exception as e:
		logging.error(f"Error occurred: {e}")

if __name__ == '__main__':
	asyncio.run(main())
