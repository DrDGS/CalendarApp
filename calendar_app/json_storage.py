import json
import os
from django.conf import settings
from datetime import datetime

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
        """Возвращает все события"""
        try:
            with open(self.events_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def add_event(self, event_data):
        """Добавляет новое событие и возвращает его с ID"""
        events = self.get_all_events()
        
        # Генерируем новый ID
        if events:
            # Находим максимальный ID
            max_id = 0
            for event in events:
                event_id = event.get('id', 0)
                if event_id > max_id:
                    max_id = event_id
            new_id = max_id + 1
        else:
            new_id = 1
        
        # Добавляем ID и время создания
        event_data['id'] = new_id
        if 'created_at' not in event_data:
            event_data['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        events.append(event_data)
        
        # Сохраняем обратно в файл
        with open(self.events_file, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        
        return event_data
    
    def get_events_by_date(self, date_str):
        """Возвращает события на определенную дату"""
        events = self.get_all_events()
        return [event for event in events if event.get("date") == date_str]
    
    def get_events_by_month(self, year, month):
        """Возвращает события за определенный месяц"""
        events = self.get_all_events()
        month_str = str(month).zfill(2)
        events_in_month = []
        
        for event in events:
            event_date = event.get("date", "")
            if event_date.startswith(f"{year}-{month_str}"):
                events_in_month.append(event)
        
        return events_in_month

# Создаем глобальный экземпляр для использования
event_storage = EventStorage()