from http.server import BaseHTTPRequestHandler
import re
from io import BytesIO
from openpyxl import Workbook
import json

def parse_ass(content):
    """Парсинг ASS файла"""
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

def parse_srt(content):
    """Парсинг SRT файла"""
    result = []
    blocks = re.split(r'\n\s*\n', content.strip())
    for block in blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if len(lines) >= 3:
            timecode = lines[1]
            text = ' '.join(lines[2:])
            result.append([timecode, text])
    return result

def handler(request):
    try:
        if request.method != 'POST':
            return {
                'statusCode': 405,
                'body': json.dumps({'error': 'Method not allowed'})
            }

        # Получаем файл из запроса
        file = request.files.get('file')
        if not file:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No file uploaded'})
            }

        content = file.read().decode('utf-8')
        filename = file.filename.lower()
        
        # Определяем формат файла
        if filename.endswith('.ass'):
            data = parse_ass(content)
        elif filename.endswith('.srt'):
            data = parse_srt(content)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Unsupported file type'})
            }

        # Создаем Excel файл
        wb = Workbook()
        ws = wb.active
        ws.append(["Время", "Текст"])
        for row in data:
            ws.append(row)
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'Content-Disposition': 'attachment; filename="converted.xlsx"'
            },
            'body': output.getvalue().decode('latin1'),
            'isBase64Encoded': False
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
