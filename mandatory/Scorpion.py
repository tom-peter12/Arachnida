import argparse
from rich_argparse import RichHelpFormatter
import os
from PIL import Image, ExifTags
from colorama import Fore

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp'}

class ExtractExifException(Exception):
	pass

class ExtractExif:
	def __init__(self, img_files):
		self.img_files = set(img_files)

	def prettified_display(self, img_file, img_exif_data):
		default_width = 35
		file_name_width = len(img_file) + 2 
		card_width = max(default_width, file_name_width)

		total_width = card_width + 19

		print(Fore.YELLOW + "╔" + "═" * total_width + "╗" + Fore.WHITE)
		print(Fore.YELLOW + "║" + " " * ((total_width - 14) // 2) + "EXIF DATA CARD" + " " * ((total_width - 14) // 2) + "║" + Fore.WHITE)
		print(Fore.YELLOW + "╠" + "═" * 17 + "╦" + "═" * (card_width) + " ╣" + Fore.WHITE)

		print(f"║ File Name       ║ {Fore.BLUE}{img_file:{card_width}}{Fore.YELLOW}║{Fore.WHITE}")
		print(Fore.YELLOW + "╠" + "═" * 17 + "╬" + "═" * card_width + "╣" + Fore.WHITE)
		
		for key, val in img_exif_data.items():
			tag_name = ExifTags.TAGS.get(key, key)
			val = str(val)
			
			lines = [val[i:i+card_width] for i in range(0, len(val), card_width)]
			print(f"║ {tag_name[:16]:<15} ║ {Fore.GREEN}{lines[0]:{card_width}} {Fore.YELLOW}║{Fore.WHITE}")
			
			for line in lines[1:]:
				print(f"║ {'':<15} ║ {Fore.GREEN}{line:{card_width}} {Fore.YELLOW}║{Fore.WHITE}")
			
			print(Fore.YELLOW + "╠" + "═" * 17 + "╬" + "═" * card_width + "╣" + Fore.WHITE)
		print()


	def extract_all(self):
		try:
			for img_file in self.img_files:
				if not (os.path.splitext(img_file)[1][1:].lower() in ALLOWED_IMAGE_EXTENSIONS):
					raise ExtractExifException('Brev please provide a valid filetype')
				else:
					image = Image.open(img_file)
					img_exif = image.getexif()
					self.prettified_display(img_file, img_exif)
		except Exception as e:
			print(e)
		

def main():
	parser = argparse.ArgumentParser(
		description="A tool to manage exif data of image/images",
		formatter_class=RichHelpFormatter
	)
	parser.add_argument(
		'imagefiles',
		metavar='F',
		type=str,
		nargs='+',
		help='A list of image files to process'
	)

	args = parser.parse_args()
	extractor = ExtractExif(args.imagefiles)
	extractor.extract_all()


if __name__ == "__main__":
	try:
		main()
	except Exception as e:
		print(e)
