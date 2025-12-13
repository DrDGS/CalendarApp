import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import uuid
import sys
import os


class SimpleICSToJSONConverter:
    """
    Упрощенный конвертер ICS в JSON без внешних зависимостей.
    """
    
    def __init__(self, timezone: str = 'UTC'):
        """
        Инициализация конвертера.
        
        Args:
            timezone (str): Часовой пояс
        """
        self.timezone = timezone
    
    def parse_ics_file(self, ics_file_path: str) -> List[Dict[str, Any]]:
        """
        Парсит файл ICS и преобразует события в JSON.
        
        Args:
            ics_file_path (str): Путь к файлу .ics
        
        Returns:
            List[Dict]: Список JSON-объектов событий
        """
        with open(ics_file_path, 'r', encoding='utf-8') as f:
            ics_content = f.read()
        
        return self.parse_ics_content(ics_content)
    
    def parse_ics_content(self, ics_content: str) -> List[Dict[str, Any]]:
        """
        Парсит содержимое ICS и преобразует события в JSON.
        
        Args:
            ics_content (str): Содержимое файла .ics
        
        Returns:
            List[Dict]: Список JSON-объектов событий
        """
        events = []
        current_event = {}
        in_event = False
        
        lines = ics_content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if line == 'BEGIN:VEVENT':
                current_event = {}
                in_event = True
            elif line == 'END:VEVENT' and in_event:
                event_json = self.event_lines_to_json(current_event)
                if event_json:
                    events.append(event_json)
                in_event = False
            elif in_event and ':' in line:
                # Обработка многострочных значений
                key, value = line.split(':', 1)
                
                # Проверяем следующую строку на продолжение (начинается с пробела)
                while i + 1 < len(lines) and lines[i + 1].startswith(' '):
                    i += 1
                    value += lines[i][1:]  # Убираем первый пробел
                
                current_event[key] = value
            
            i += 1
        
        return events
    
    def event_lines_to_json(self, event_lines: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Преобразует строки события в JSON-объект.
        
        Args:
            event_lines (Dict): Словарь строк события
        
        Returns:
            Dict: JSON-объект события
        """
        try:
            event_id = event_lines.get('UID', str(uuid.uuid4()))
            
            # Обработка даты начала
            dtstart = event_lines.get('DTSTART')
            start_dt = self.parse_ics_datetime(dtstart) if dtstart else datetime.now()
            start_dt += timedelta(hours=3)
            # Обработка даты окончания
            dtend = event_lines.get('DTEND')
            end_dt = self.parse_ics_datetime(dtend) if dtend else start_dt + timedelta(hours=1)
            end_dt += timedelta(hours=3)
            # Проверяем на событие на весь день
            is_all_day = 'VALUE=DATE' in event_lines.get('DTSTART;', '')
            
            # Обработка RRULE
            rrule_str = event_lines.get('RRULE')
            rrule_data = self.parse_simple_rrule(rrule_str) if rrule_str else None
            
            # Создание JSON-объекта
            event_json = {
                'id': event_id,
                'title': event_lines.get('SUMMARY', 'Без названия'),
                'description': event_lines.get('DESCRIPTION', ''),
                'location': event_lines.get('LOCATION', ''),
                'start_datetime': start_dt.isoformat(),
                'end_datetime': end_dt.isoformat(),
                'all_day': is_all_day,
                'created': datetime.now().isoformat(),
                'last_modified': datetime.now().isoformat(),
                'rrule': rrule_data,
                'metadata': {
                    'source': 'ics',
                    'converted_at': datetime.now().isoformat(),
                    'timezone': self.timezone
                }
            }
            
            # Добавляем дополнительные поля
            if 'ORGANIZER' in event_lines:
                event_json['organizer'] = event_lines['ORGANIZER']
            
            if 'STATUS' in event_lines:
                event_json['status'] = event_lines['STATUS']
            
            if 'CATEGORIES' in event_lines:
                categories = event_lines['CATEGORIES'].split(',')
                event_json['categories'] = [c.strip() for c in categories]
            
            return event_json
            
        except Exception as e:
            print(f"Ошибка при преобразовании события: {e}")
            return None
    
    def parse_ics_datetime(self, dt_str: str) -> datetime:
        """
        Парсит строку даты из ICS в datetime.
        
        Args:
            dt_str (str): Строка даты из ICS
        
        Returns:
            datetime: Объект datetime
        """
        try:
            # Удаляем параметры (например, ;TZID=Europe/Moscow)
            if ';' in dt_str:
                dt_str = dt_str.split(';')[0]
            
            # Форматы ICS: 20240115T090000 или 20240115
            if 'T' in dt_str:
                # С датой и временем
                date_str, time_str = dt_str.split('T')
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                
                if len(time_str) >= 6:
                    hour = int(time_str[:2])
                    minute = int(time_str[2:4])
                    second = int(time_str[4:6]) if len(time_str) >= 6 else 0
                else:
                    hour = minute = second = 0
                
                return datetime(year, month, day, hour, minute, second)
            else:
                # Только дата (событие на весь день)
                year = int(dt_str[:4])
                month = int(dt_str[4:6])
                day = int(dt_str[6:8])
                return datetime(year, month, day)
                
        except Exception as e:
            print(f"Ошибка парсинга даты {dt_str}: {e}")
            return datetime.now()
    
    def parse_simple_rrule(self, rrule_str: str) -> Optional[Dict[str, Any]]:
        """
        Простой парсер RRULE.
        
        Args:
            rrule_str (str): Строка RRULE
        
        Returns:
            Dict: Разобранное правило повторения
        """
        rrule_dict = {}
        
        # Разделяем параметры
        parts = rrule_str.split(';')
        
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                key = key.strip().upper()
                
                if key == 'FREQ':
                    rrule_dict['FREQ'] = value
                elif key == 'UNTIL':
                    # Парсим дату окончания
                    try:
                        until_dt = self.parse_ics_datetime(value)
                        rrule_dict['UNTIL'] = until_dt.isoformat()
                    except:
                        rrule_dict['UNTIL'] = value
                elif key == 'INTERVAL':
                    try:
                        rrule_dict['INTERVAL'] = int(value)
                    except:
                        pass
                elif key == 'COUNT':
                    try:
                        rrule_dict['COUNT'] = int(value)
                    except:
                        pass
                elif key == 'BYDAY':
                    rrule_dict['BYDAY'] = value.split(',')
                else:
                    rrule_dict[key] = value
        
        return rrule_dict if rrule_dict else None
    
    def save_to_file(self, events: List[Dict[str, Any]], 
                    output_file: str = 'schedule_file.txt') -> None:
        """
        Сохраняет список JSON-объектов в текстовый файл.
        
        Args:
            events (List): Список JSON-объектов событий
            output_file (str): Имя выходного файла
        """
        # Преобразуем в формат, где каждый JSON на отдельной строке
        json_strings = []
        for event in events:
            json_str = json.dumps(event, ensure_ascii=False, default=str)
            json_strings.append(json_str)
        
        # Записываем в файл, каждое событие на новой строке
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(json_strings))
        
        print(f"Сохранено {len(events)} событий в файл {output_file}")
