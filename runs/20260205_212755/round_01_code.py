from pathlib import Path
Path('hello.txt').write_text('hello', encoding='utf-8')
print('wrote hello.txt')
