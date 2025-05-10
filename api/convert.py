from http.server import BaseHTTPRequestHandler
import re
from io import BytesIO
from openpyxl import Workbook
import json

def parse_subtitle(content, filename):
    """Определяем формат и парсим файл"""
    if filename.lower().endswith('.ass'):
        return parse_ass(content)
    elif filename.lower().endswith('.srt'):
        return parse_srt(content)
    raise ValueError("Unsupported file format")

def parse_ass(content):
    """Парсинг ASS формата"""
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
    """Парсинг SRT формата"""
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
                'body': json.dumps({'error': 'Only POST method allowed'})
            }

        if 'file' not in request.files:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No file uploaded'})
            }

        file = request.files['file']
        content = file.read().decode('utf-8')
        
        data = parse_subtitle(content, file.filename)
        
        wb = Workbook()
        ws = wb.active
        ws.append(["Time", "Text"])
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
