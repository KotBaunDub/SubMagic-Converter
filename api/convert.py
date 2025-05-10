from http.server import BaseHTTPRequestHandler
import re
from io import BytesIO
from openpyxl import Workbook

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # Простая обработка multipart/form-data
            boundary = self.headers['Content-Type'].split('=')[1].encode()
            parts = post_data.split(boundary)
            file_data = None
            
            for part in parts:
                if b'filename="' in part:
                    file_data = part.split(b'\r\n\r\n')[1].rstrip(b'\r\n--')
                    break

            if not file_data:
                self.send_error(400, "No file uploaded")
                return

            content = file_data.decode('utf-8')
            
            # Определяем формат файла
            if 'Dialogue:' in content:  # ASS формат
                data = self.parse_ass(content)
            else:  # SRT формат
                data = self.parse_srt(content)
            
            # Создаем Excel файл
            excel_file = self.create_excel(data)
            
            # Отправляем ответ
            self.send_response(200)
            self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            self.send_header('Content-Disposition', 'attachment; filename="converted.xlsx"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(excel_file.getvalue())
            
        except Exception as e:
            self.send_error(500, f"Error: {str(e)}")

    def parse_ass(self, content):
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

    def parse_srt(self, content):
        result = []
        blocks = re.split(r'\n\s*\n', content.strip())
        for block in blocks:
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            if len(lines) >= 3:
                timecode = lines[1]
                text = ' '.join(lines[2:])
                result.append([timecode, text])
        return result

    def create_excel(self, data):
        wb = Workbook()
        ws = wb.active
        ws.append(["Время", "Текст"])
        for row in data:
            ws.append(row)
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output
