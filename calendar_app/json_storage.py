import json
import os
from django.conf import settings
from datetime import datetime, date
from dateutil.parser import parse as parse_date
import uuid

class EventStorage:
    def __init__(self):
        self.events_file = os.path.join(settings.BASE_DIR, 'calendar_app', 'events.json')
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Создает файл events.json, если он не существует"""
        if not os.path.exists(self.events_file):
            # Создаем пустой список событий
            empty_data = []
            with open(self.events_file, 'w', encoding='utf-8') as f:
                json.dump(empty_data, f, ensure_ascii=False, indent=2)
    
    def get_all_events(self):
        """Возвращает все события в исходном формате"""
        try:
            with open(self.events_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def add_event(self, event_data):
        """Добавляет новое событие в формате ICS и возвращает его с ID"""
        events = self.get_all_events()
        
        # Генерируем уникальный ID если его нет
        if 'id' not in event_data:
            event_data['id'] = str(uuid.uuid4()).replace('-', '')[:20]
        
        # Добавляем время создания если его нет
        if 'created' not in event_data:
            event_data['created'] = datetime.now().isoformat()
        
        # Добавляем время последнего изменения
        event_data['last_modified'] = datetime.now().isoformat()
        
        # Если нет metadata, добавляем пустой объект
        if 'metadata' not in event_data:
            event_data['metadata'] = {
                'source': 'manual',
                'converted_at': datetime.now().isoformat()
            }
        
        events.append(event_data)
        
        # Сохраняем обратно в файл
        with open(self.events_file, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2, default=str)
        
        return event_data
    
    def update_event(self, event_id, event_data):
        """Обновляет существующее событие"""
        events = self.get_all_events()
        
        for i, event in enumerate(events):
            if event.get('id') == event_id:
                # Обновляем поля
                event_data['id'] = event_id
                event_data['last_modified'] = datetime.now().isoformat()
                
                # Сохраняем оригинальную дату создания
                if 'created' in event:
                    event_data['created'] = event['created']
                
                events[i] = event_data
                
                # Сохраняем обновленный список
                with open(self.events_file, 'w', encoding='utf-8') as f:
                    json.dump(events, f, ensure_ascii=False, indent=2, default=str)
                return True
        
        return False
    
    def delete_event(self, event_id):
        """Удаляет событие по ID и возвращает True если удалено, False если не найдено"""
        events = self.get_all_events()
        
        # Находим индекс события
        for i, event in enumerate(events):
            if event.get('id') == event_id:
                # Удаляем событие
                del events[i]
                # Сохраняем обновленный список
                with open(self.events_file, 'w', encoding='utf-8') as f:
                    json.dump(events, f, ensure_ascii=False, indent=2, default=str)
                return True
        
        return False
    
    def get_event_by_id(self, event_id):
        """Возвращает событие по ID"""
        events = self.get_all_events()
        for event in events:
            if event.get('id') == event_id:
                return event
        return None
    
    def get_events_by_date(self, date_str):
        """Возвращает события на определенную дату (с учетом повторяющихся)"""
        events = self.get_all_events()
        target_date = parse_date(date_str).date() if isinstance(date_str, str) else date_str
        
        result_events = []
        
        for event in events:
            # Проверяем начальную дату события
            start_datetime_str = event.get('start_datetime')
            if not start_datetime_str:
                continue
                
            try:
                event_start = parse_date(start_datetime_str).date()
                
                # Проверяем события с повторениями
                if event.get('rrule'):
                    from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY
                    
                    rrule_data = event.get('rrule', {})
                    freq_str = rrule_data.get('FREQ', 'WEEKLY')
                    interval = rrule_data.get('INTERVAL', 1)
                    until_str = rrule_data.get('UNTIL')
                    
                    # Преобразуем частоту
                    freq_map = {'DAILY': DAILY, 'WEEKLY': WEEKLY, 'MONTHLY': MONTHLY}
                    got_freq = freq_map.get(freq_str)
                    
                    if got_freq:
                        # Создаем datetime для начала события
                        from datetime import datetime as dt_class
                        event_datetime = parse_date(start_datetime_str)
                        
                        # Определяем дату окончания
                        until = None
                        if until_str:
                            try:
                                until = parse_date(until_str)
                            except:
                                until = None
                        
                        # Генерируем даты повторений и проверяем попадает ли целевая дата
                        dates = list(rrule(
                            freq=got_freq,
                            interval=interval,
                            dtstart=event_datetime,
                            until=until
                        ))
                        
                        for dt in dates:
                            if dt.date() == target_date:
                                result_events.append(event)
                                break
                else:
                    # Обычное событие без повторений
                    if event_start == target_date:
                        result_events.append(event)
                        
            except Exception as e:
                print(f"Error processing event date: {e}")
                continue
        
        return result_events
    
    def get_events_by_month(self, year, month):
        """Возвращает события за определенный месяц (с учетом повторяющихся)"""
        events = self.get_all_events()
        
        result_events = []
        
        for event in events:
            start_datetime_str = event.get('start_datetime')
            date_str = event.get('date')
            if not start_datetime_str and not date_str:
                continue
            if start_datetime_str:
                try:
                    event_start = parse_date(start_datetime_str).date()
                    
                    # Проверяем события с повторениями
                    if event.get('rrule'):
                        from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY
                        
                        rrule_data = event.get('rrule', {})
                        freq_str = rrule_data.get('FREQ', 'WEEKLY')
                        interval = rrule_data.get('INTERVAL', 1)
                        until_str = rrule_data.get('UNTIL')
                        
                        # Преобразуем частоту
                        freq_map = {'DAILY': DAILY, 'WEEKLY': WEEKLY, 'MONTHLY': MONTHLY}
                        got_freq = freq_map.get(freq_str)
                        
                        if got_freq:
                            event_datetime = parse_date(start_datetime_str)
                            
                            # Определяем дату окончания
                            until = None
                            if until_str:
                                try:
                                    until = parse_date(until_str)
                                except:
                                    until = None
                            
                            # Генерируем даты повторений и проверяем попадают ли они в нужный месяц
                            dates = list(rrule(
                                freq=got_freq,
                                interval=interval,
                                dtstart=event_datetime,
                                until=until
                            ))
                            
                            for dt in dates:
                                if dt.year == year and dt.month == month:
                                    result_events.append(event)
                                    break
                    else:
                        # Обычное событие без повторений
                        if event_start.year == year and event_start.month == month:
                            result_events.append(event)
                            
                except Exception as e:
                    print(f"Error processing event for month: {e}")
                    continue
            else:
                try:
                    event_start = parse_date(date_str).date()
                    if event_start.year == year and event_start.month == month:
                        result_events.append(event)
                except Exception as e:
                    print(f"Error processing event for month: {e}")
                    continue
        return result_events
    
    def get_recurring_events(self):
        """Возвращает все повторяющиеся события"""
        events = self.get_all_events()
        return [event for event in events if event.get('rrule')]
    
    def get_non_recurring_events(self):
        """Возвращает все неповторяющиеся события"""
        events = self.get_all_events()
        return [event for event in events if not event.get('rrule')]
    
    def import_events_from_list(self, events_list):
        """Импортирует список событий"""
        existing_events = self.get_all_events()
        
        # Добавляем новые события
        for event in events_list:
            # Проверяем, есть ли уже такое событие
            existing = False
            for existing_event in existing_events:
                if existing_event.get('id') == event.get('id'):
                    existing = True
                    break
            
            if not existing:
                # Добавляем время импорта в metadata
                if 'metadata' not in event:
                    event['metadata'] = {}
                event['metadata']['imported_at'] = datetime.now().isoformat()
                
                existing_events.append(event)
        
        # Сохраняем обновленный список
        with open(self.events_file, 'w', encoding='utf-8') as f:
            json.dump(existing_events, f, ensure_ascii=False, indent=2, default=str)
        
        return len(events_list)
    
    def search_events(self, query, field=None):
        """Поиск событий по текстовому запросу"""
        events = self.get_all_events()
        
        if not query:
            return events
        
        query_lower = query.lower()
        results = []
        
        for event in events:
            found = False
            
            if field:
                # Поиск в конкретном поле
                value = event.get(field, '')
                if query_lower in str(value).lower():
                    found = True
            else:
                # Поиск во всех текстовых полях
                text_fields = ['title', 'description', 'location']
                for field_name in text_fields:
                    value = event.get(field_name, '')
                    if query_lower in str(value).lower():
                        found = True
                        break
            
            if found:
                results.append(event)
        
        return results
    
    def get_events_by_type(self, event_type):
        """Возвращает события определенного типа"""
        events = self.get_all_events()
        
        # Определяем тип события по заголовку/описанию
        def check_event_type(event):
            title = event.get('title', '').lower()
            description = event.get('description', '').lower()
            
            if event_type == 'lecture':
                return 'лекция' in title or 'лекция' in description
            elif event_type == 'seminar':
                return 'семинар' in title or 'семинар' in description
            elif event_type == 'lab':
                return 'лаб' in title or 'лабораторная' in title or 'лаб' in description
            elif event_type == 'exam':
                return 'экзамен' in title or 'экзамен' in description
            else:
                return True
        
        return [event for event in events if check_event_type(event)]


# Создаем глобальный экземпляр для использования
event_storage = EventStorage()