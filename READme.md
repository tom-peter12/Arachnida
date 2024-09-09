# Arachnida

Arachnida is a Python-based project consisting of two main programs:

1. **Web Image Scraping (Spider)**: A recursive image scraper designed to efficiently download images from websites, with support for recursion depth and optimized resource management for large-scale recursions.
2. **EXIF Data Extraction (Scorpion)**: A tool for extracting and displaying EXIF metadata from images, including camera settings and GPS information, with options for both command-line and GUI modes.

## Technologies Used

- **Programming Language**: Python 3
- **Libraries**: `asyncio`, `aiohttp`, `concurrent.futures`, `exifread`, `PIL (Pillow)`, `lxml`
- **GUI Framework**: Tkinter

### Program Details

#### 1. Web Image Scraping (Spider)
The scraper mimics the behavior of the GNU `wget` utility, particularly its breadth-first approach for recursively downloading files over HTTP/S. By utilizing asynchronous I/O (`asyncio` and `aiohttp`), this program handles I/O-bound operations efficiently. For CPU-bound tasks, such as unique name generation for image files using MD5 hash, the `concurrent.futures` library is used, ensuring optimized performance for large-scale scraping tasks.

#### 2. EXIF Data Extraction (Scorpion)
This tool behaves similarly to `ExifTool` by Phil Harvey, leveraging the `exifread` library to parse EXIF data and `PIL` (Pillow) for image processing tasks, such as deleting EXIF metadata. A graphical interface built with Tkinter allows users to view EXIF data in a readable format, while the command-line version offers detailed metadata extraction.


## How to Run

### Web Image Scraper (Spider)
1. Clone the repository:
   ```bash
   git clone https://github.com/tom-peter12/arachnida.git
   cd arachnida
   ```
2. Create and set up a virtual environment
   ```bash
   python3 -m venv env
   source env/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the scraper:
   ```bash
   python3 spider.py [-h] [-r] [-l LEVEL] [-p PATH] URL 
   ```
   - `-h`: Help message
   - `-r`: Recursive mode
   - `-l LEVEL`: Recursion depth
   - `-p PATH`: Output directory path
   - `URL`: Website URL to scrape

### EXIF Data Extraction (Scorpion)
3. Run the program:
   ```bash
   python3 scorpion.py [-h] [-g] [-d] [FILE ...]
   ```
   - `-h`: Help message
   - `-g`: GUI mode
   - `-d`: Delete EXIF data
   - `FILE`: Image file path


## Optimizations

Throughout the development process, multiple iterations were implemented to optimize performance, especially in the web scraping module. The use of asynchronous programming (via `asyncio` and `aiohttp`) for I/O-bound operations and concurrency (via `concurrent.futures`) for CPU-bound tasks significantly reduced memory consumption and runtime.


## Performance Comparison: spider vs. GNU wget

A detailed time comparison was conducted between Arachnida’s web scraper and GNU wget using the same URL and recursion depth:


| Test URL                        | Recursion Depth | Arachnida (Time) | GNU `wget` (Time) |
|---------------------------------|-----------------:|------------------:|-------------------:|
| [https://ollivere.co/](https://ollivere.co/) | 1               | 0.523s         | 3.055s          |
| [https://ollivere.co/](https://ollivere.co/) | 2               | 19.066s         | 13.010s          |


**Note**: The command used for GNU `wget` was:
```bash
	wget -r -l LEVEL -A jpg,jpeg,png,gif,bmp --no-parent -nd -P ./data <URL>
```


## Lessons Learned

Working on Arachnida provided invaluable experience in managing resources for large-scale web scraping. Optimizing recursion strategies and parallel execution taught me how to balance performance with memory efficiency. Additionally, I deepened my understanding of image metadata, the complexities of EXIF data across formats, and learned to develop user-friendly GUIs using Tkinter.

**Key Takeaways** 
- Breadth-first Graph traversal
- Argument Parsing
- HTTP requests
- HTML parsing using lxml
- Web Scrapping
- Concurrency for CPU Bound Tasks
- Async programming for I/O Bound Tasks
- EXIF Data
- Tkinter Graphics 


