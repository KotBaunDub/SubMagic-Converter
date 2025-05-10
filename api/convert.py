from http.server import BaseHTTPRequestHandler
import re
from io import BytesIO
from openpyxl import Workbook

class SubtitleParser:
    @staticmethod
    def parse(content, ext):
        if ext == '.ass':
            return SubtitleParser.parse_ass(content)
        return SubtitleParser.parse_srt(content)

    @staticmethod
    def parse_ass(content):
        result = []
        in_events = False
        for line in content.splitlines():
            line = line.strip()
            if line == "[Events]":
                in_events = True
                continue
            if in_events and line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                time = parts[1].strip()
                text = re.sub(r'\{.*?\}', '', parts[9]).replace("\\N", " ")
                result.append([time, text])
        return result

    @staticmethod
    def parse_srt(content):
        result = []
        blocks = re.split(r'\n\s*\n', content.strip())
        for block in blocks:
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            if len(lines) >= 3:
                timecode = lines[1]
                text = ' '.join(lines[2:])
                result.append([timecode, text])
        return result

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            file_data = self.rfile.read(content_length)
            
            # Извлекаем файл
            boundary = self.headers['Content-Type'].split('=')[1].encode()
            parts = [p for p in file_data.split(boundary) if b'filename="' in p]
            if not parts:
                self.send_error(400, "No file uploaded")
                return
                
            filename_part = parts[0].split(b'; filename="')[1].split(b'"')[0]
            filename = filename_part.decode()
            ext = '.ass' if filename.lower().endswith('.ass') else '.srt'
            
            content = parts[0].split(b'\r\n\r\n')[1].rstrip(b'\r\n--').decode('utf-8')
            
            # Парсим и конвертируем
            data = SubtitleParser.parse(content, ext)
            wb = Workbook()
            ws = wb.active
            ws.append(["Время", "Текст"])
            for row in data:
                ws.append(row)
            
            # Отправляем результат
            output = BytesIO()
            wb.save(output)
            output.seek(0)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            self.send_header('Content-Disposition', f'attachment; filename="converted.xlsx"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(output.getvalue())
            
        except Exception as e:
            self.send_error(500, f"Server Error: {str(e)}")
