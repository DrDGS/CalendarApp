from django.shortcuts import render, redirect
from datetime import datetime, date
from django.utils import timezone
from django.core.files.storage import FileSystemStorage
from django.views.decorators.csrf import csrf_exempt

import os
from calendar_app.schedule.ICSToJSONConverter import SimpleICSToJSONConverter
from calendar_app.schedule.giga import giga
from .json_storage import EventStorage, event_storage
import json
from django.conf import settings
import requests
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from django.utils import timezone
from datetime import datetime
import calendar as cal_module
import json
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY
from dateutil.parser import parse as parse_date

def calendar_view(request):
    # Получаем текущую дату с учетом локального времени
    today = timezone.localtime(timezone.now()).date()
    
    # Получаем год и месяц из GET-параметров или используем текущие
    year = request.GET.get('year', today.year)
    month = request.GET.get('month', today.month)
    
    # Преобразуем в целые числа
    try:
        year = int(year)
        month = int(month)
    except (ValueError, TypeError):
        year = today.year
        month = today.month
    
    # Проверяем валидность месяца
    if month < 1:
        month = 1
    elif month > 12:
        month = 12
    
    # Создаем объект календаря (0 = понедельник, 6 = воскресенье)
    cal = cal_module.Calendar(firstweekday=0)
    
    # Получаем дни месяца в виде матрицы (список списков)
    month_days = cal.monthdayscalendar(year, month)
    
    # Названия месяцев на русском
    month_names = [
        'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ]
    
    # Названия дней недели на русском
    weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    
    # Получаем события для текущего месяца
    all_events = event_storage.get_events_by_month(year, month)
    
    # Функция для определения типа события
    def detect_event_type(event):
        title = event.get('title', '').lower()
        description = event.get('description', '').lower()
        
        if 'лекция' in title or 'лекция' in description:
            return 'lecture'
        elif 'семинар' in title or 'семинар' in description:
            return 'seminar'
        elif 'лаб' in title or 'лабораторная' in title or 'лаб' in description:
            return 'lab'
        elif 'экзамен' in title or 'экзамен' in description:
            return 'exam'
        elif 'дедлайн' in title or 'дедлайн' in description:
            return 'deadline'
        else:
            return 'other'
    
    # Обрабатываем события и их повторения
    processed_events = []
    events_by_day = {}
    recurring_count = 0
    
    for event in all_events:
        # Базовые данные события
        event_data = {
            'id': event.get('id'),
            'title': event.get('title', 'Без названия'),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'event_type': detect_event_type(event),
            'is_recurring': False,
            'date': None,
            'start_time': None,
            'end_time': None,
            'rrule': None
        }
        
        # Определяем тип события для отображения
        event_type_display_map = {
            'lecture': 'Лекция',
            'seminar': 'Семинар', 
            'lab': 'Лабораторная',
            'exam': 'Экзамен',
            'deadline': 'Дедлайн',
            'other': 'Другое'
        }
        event_data['event_type_display'] = event_type_display_map.get(event_data['event_type'], 'Другое')
        
        # Обрабатываем дату и время
        start_datetime = event.get('start_datetime')
        end_datetime = event.get('end_datetime')
        all_day = event.get('all_day', False)
        
        if start_datetime:
            try:
                # Парсим дату-время
                if isinstance(start_datetime, str):
                    dt_start = parse_date(start_datetime)
                else:
                    dt_start = start_datetime

                if isinstance(end_datetime, str):
                    dt_end = parse_date(end_datetime)
                else:
                    dt_end = end_datetime
                
                event_data['date'] = dt_start.date()
                
                # Время для отображения
                if not all_day:
                    event_data['start_time'] = dt_start.strftime('%H:%M')
                    event_data['end_time'] = dt_end.strftime('%H:%M')
                    
                    if end_datetime:
                        if isinstance(end_datetime, str):
                            dt_end = parse_date(end_datetime)
                        else:
                            dt_end = end_datetime
                        
                        # Рассчитываем продолжительность в минутах
                        duration_minutes = int((dt_end - dt_start).total_seconds() / 60)
                        event_data['duration'] = duration_minutes
            except Exception as e:
                print(f"Error parsing datetime: {e}")
                continue
        
        # Обрабатываем повторяющиеся события (RRULE)
        rrule_data = event.get('rrule')
        if rrule_data:
            event_data['is_recurring'] = True
            event_data['rrule'] = rrule_data
            recurring_count += 1
            
            try:
                # Генерируем даты повторений для текущего месяца
                freq_map = {
                    'DAILY': DAILY,
                    'WEEKLY': WEEKLY, 
                    'MONTHLY': MONTHLY,
                    'YEARLY': None  # Добавьте при необходимости
                }
                
                freq_str = rrule_data.get('FREQ', 'WEEKLY')
                freq = freq_map.get(freq_str, WEEKLY)
                
                if freq is None:
                    continue  # Пропускаем неподдерживаемые частоты
                
                interval = rrule_data.get('INTERVAL', 1)
                until_str = rrule_data.get('UNTIL')
                
                # Определяем дату окончания повторений
                until = None
                if until_str:
                    try:
                        until = parse_date(until_str)
                    except:
                        until = None
                
                # Определяем начальную дату события
                if event_data['date']:
                    dtstart = datetime.combine(
                        event_data['date'], 
                        datetime.min.time() if all_day else dt_start.time()
                    )
                else:
                    continue  # Нет начальной даты
                
                # Генерируем все даты повторений
                try:
                    dates = list(rrule(
                        freq=freq,
                        interval=interval,
                        dtstart=dtstart,
                        until=until
                    ))
                    
                    # Фильтруем даты, попадающие в текущий месяц
                    for dt in dates:
                        if dt.year == year and dt.month == month:
                            # Создаем копию события для этой даты
                            event_copy = event_data.copy()
                            event_copy['date'] = dt.date()
                            event_copy['original_date'] = event_data['date']
                            
                            if not all_day:
                                event_data['start_time'] = dt_start.strftime('%H:%M')
                                event_data['end_time'] = dt_end.strftime('%H:%M')
                            
                            # Добавляем в общий список
                            processed_events.append(event_copy)
                            
                            # Добавляем в словарь по дням
                            day = dt.day
                            if day not in events_by_day:
                                events_by_day[day] = []
                            events_by_day[day].append(event_copy)
                except Exception as e:
                    print(f"Error generating recurring dates: {e}")
                    # Добавляем исходное событие как одиночное
                    if event_data['date']:
                        processed_events.append(event_data)
                        
                        day = event_data['date'].day
                        if day not in events_by_day:
                            events_by_day[day] = []
                        events_by_day[day].append(event_data)
            except Exception as e:
                print(f"Error processing rrule: {e}")
                # Добавляем как обычное событие
                if event_data['date']:
                    processed_events.append(event_data)
                    
                    day = event_data['date'].day
                    if day not in events_by_day:
                        events_by_day[day] = []
                    events_by_day[day].append(event_data)
        else:
            # Обычное (не повторяющееся) событие
            if event_data['date']:
                processed_events.append(event_data)
                
                day = event_data['date'].day
                if day not in events_by_day:
                    events_by_day[day] = []
                events_by_day[day].append(event_data)
    
    # Сортируем события по времени
    for day in events_by_day:
        events_by_day[day] = sorted(
            events_by_day[day], 
            key=lambda x: (x['date'], x.get('start_time', '') if x.get('start_time') else '')
        )
    
    # Сортируем общий список событий
    processed_events = sorted(
        processed_events,
        key=lambda x: (x['date'], x.get('start_time', '') if x.get('start_time') else '')
    )
    
    # Подготавливаем JSON для шаблона
    events_json = []
    for event in processed_events:
        events_json.append({
            'id': event.get('id'),
            'title': event.get('title'),
            'date': event.get('date').isoformat() if event.get('date') else '',
            'start_time': event.get('start_time'),
            'end_time': event.get('end_time'),
            'event_type': event.get('event_type'),
            'location': event.get('location'),
            'is_recurring': event.get('is_recurring'),
            'difficulty': event.get('difficulty', 0),  # если есть поле сложности
            'time_required': event.get('time_required', 0)  # если есть поле временных затрат
        })
    
    # Получаем предыдущий и следующий месяцы для навигации
    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1
    
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1
    
    # Подготавливаем данные для шаблона
    context = {
        'year': year,
        'month': month,
        'month_name': month_names[month - 1],
        'month_days': month_days,
        'weekdays': weekdays,
        'today': today,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'events_by_day': events_by_day,
        'all_events': processed_events,
        'all_events_json': json.dumps(events_json, ensure_ascii=False, default=str),
        'recurring_count': recurring_count,
    }
    
    return render(request, 'calendar_app/calendar.html', context)


def analyze_docx_file(file_path):
    file_response = giga.upload_file(open(file_path, 'rb'))
    analyze_res = giga.chat(
        {
            "function_call": "auto",
            "messages": [
                {
                    "role": "user",
                    "content": "Представь, что я сильный студент мгту им. баумана, который использует ии для выполнения работ."\
                    "Мне не нужны твои размышления, нужен только ответ согласно приложенному шаблону: "\
                    "по шкале от 1 до 10 оцени времязатратность и сложность выполнения всей работы согласно приложенному файлу"\
                    " и ответь в формате \"времязатратность:число, сложность:число\" таким образом, чтобы мне было удобно вычленить ответ из http-ответа.",
                    "attachments": [file_response.id_],
                }
            ],
            "temperature": 0.2
        }
    )
    results = list(filter(lambda x: x != "", analyze_res.choices[0].message.content.replace("*", "").split(" ")))
    print(results)
    return int(results[0].split(":")[-1]), int(results[1].split(":")[-1]), "Потому что так сказал Gigachat!"

def handle_file_analysis(request):
    try:
        uploaded_file = request.FILES['file']
        
        # Проверяем тип файла
        if not uploaded_file.name.lower().endswith(('.docx', '.doc')):
            return JsonResponse({
                'success': False,
                'error': 'Поддерживаются только файлы формата DOCX и DOC'
            })
        
        # Проверяем размер файла (макс. 10 МБ)
        if uploaded_file.size > 10 * 1024 * 1024:
            return JsonResponse({
                'success': False,
                'error': 'Файл слишком большой. Максимальный размер: 10 МБ'
            })
        # Сохраняем файл временно
        fs = FileSystemStorage(location='temp_uploads')
        filename = fs.save(uploaded_file.name, uploaded_file)
        file_path = fs.path(filename)
        
        try:
            # Анализируем файл и получаем сложность и времензатратность
            difficulty, time_required, explanation = analyze_docx_file(file_path)
            
            return JsonResponse({
                'success': True,
                'difficulty': difficulty,
                'time_required': time_required,
                'explanation': explanation
            })
            
        finally:
            # Удаляем временный файл
            if os.path.exists(file_path):
                os.remove(file_path)
                
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при обработке файла: {str(e)}'
        })

def handle_form_submission(request):
    """Обработка отправки основной формы"""
    # Получаем данные из формы
    name = request.POST.get('name', '').strip()
    subject = request.POST.get('subject', '').strip()
    
    # Если выбрано "Другой предмет", берем значение из custom_subject
    if subject == 'other':
        subject = request.POST.get('custom_subject', '').strip()
    
    difficulty = request.POST.get('difficulty', '5')
    time_required = request.POST.get('time_required', '5')
    date = request.POST.get('date', '')
    
    # Получаем загруженный файл (если есть)
    uploaded_file = None
    if 'document_file' in request.FILES:
        uploaded_file = request.FILES['document_file']
    
    # Валидация данных
    if not name or not subject or not date:
        return render(request, 'calendar_app/add_event.html', {
            'error': 'Все поля обязательны для заполнения',
            'form_data': request.POST,
            'selected_date': date
        })
    
    try:
        # Преобразуем в числа
        difficulty_int = int(difficulty)
        time_int = int(time_required)
        
        # Проверяем диапазоны
        if not (1 <= difficulty_int <= 10) or not (1 <= time_int <= 10):
            return render(request, 'calendar_app/add_event.html', {
                'error': 'Сложность и временязатратность должны быть от 1 до 10',
                'form_data': request.POST,
                'selected_date': date
            })
        
        # Сохраняем файл (если был загружен)
        file_url = None
        if uploaded_file:
            # Проверяем тип файла
            if not uploaded_file.name.lower().endswith(('.docx', '.doc', '.pdf')):
                return render(request, 'calendar_app/add_event.html', {
                    'error': 'Поддерживаются только файлы формата DOCX, DOC и PDF',
                    'form_data': request.POST,
                    'selected_date': date
                })
            
            # Проверяем размер файла
            if uploaded_file.size > 10 * 1024 * 1024:  # 10 МБ
                return render(request, 'calendar_app/add_event.html', {
                    'error': 'Файл слишком большой. Максимальный размер: 10 МБ',
                    'form_data': request.POST,
                    'selected_date': date
                })
            
            # Сохраняем файл
            fs = FileSystemStorage(location='media/uploads')
            filename = fs.save(f"deadlines/{uploaded_file.name}", uploaded_file)
            file_url = fs.url(filename)
        
        # Создаем объект события
        new_event_data = {
            'name': name,
            'subject': subject,
            'difficulty': difficulty_int,
            'time_required': time_int,
            'date': date,
        }
        
        # Добавляем информацию о файле, если он был загружен
        if file_url:
            new_event_data['file_url'] = file_url
            if uploaded_file:
                new_event_data['file_name'] = uploaded_file.name
        
        # Добавляем событие через storage
        new_event = event_storage.add_event(new_event_data)
        
        # Перенаправляем на календарь
        return redirect('calendar_app:calendar')
        
    except ValueError:
        return render(request, 'calendar_app/add_event.html', {
            'error': 'Некорректные данные в числовых полях',
            'form_data': request.POST,
            'selected_date': date
        })
    except Exception as e:
        return render(request, 'calendar_app/add_event.html', {
            'error': f'Ошибка при сохранении: {str(e)}',
            'form_data': request.POST,
            'selected_date': date
        })

def add_event_view(request):
    """Страница добавления нового события"""
    if request.method == 'POST':
        # Проверяем, является ли запрос AJAX запросом для анализа файла
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 'file' in request.FILES:
            return handle_file_analysis(request)
        
        # Обычная отправка формы
        return handle_form_submission(request)
    
    # GET запрос - показываем пустую форму
    selected_date = request.GET.get('date', '')
    today = timezone.localtime(timezone.now()).date().strftime("%Y-%m-%d")
    
    # Если передана дата из календаря, используем её, иначе - сегодня
    if selected_date:
        default_date = selected_date
    else:
        default_date = today
    
    return render(request, 'calendar_app/add_event.html', {
        'selected_date': selected_date,
        'default_date': default_date,
        'today': today
    })


def delete_event_view(request, event_id):
    """Удаление события по ID"""
    if request.method == 'POST':
        try:
            # Используем метод delete_event из event_storage
            success = event_storage.delete_event(event_id)
            
            if success:
                # Перенаправляем на календарь с сообщением об успехе
                return redirect('calendar_app:calendar')
            else:
                # Если событие не найдено, все равно перенаправляем на календарь
                return redirect('calendar_app:calendar')
                
        except Exception as e:
            # В случае ошибки возвращаем на календарь
            print(f"Ошибка при удалении события: {e}")  # Для отладки
            return redirect('calendar_app:calendar')
    
    # Если не POST запрос, перенаправляем на календарь
    return redirect('calendar_app:calendar')

def get_ai_analysis(request):
    """Получает случайный текст для анализа"""
    try:
        # Вариант 1: Получаем случайный текст с lorem-ipsum API
        response = requests.get('https://loripsum.net/api/1/short/plaintext', timeout=5)
        
        # Проверяем статус ответа
        if response.status_code == 200:
            text = response.text.strip()
            return JsonResponse({
                'success': True,
                'text': text[:500]  # Ограничиваем длину
            })
        else:
            # Если не получилось, используем fallback текст
            return JsonResponse({
                'success': True,
                'text': "Анализ расписания: Ваши дедлайны распределены равномерно. Рекомендуется начать с задания по математике, так как оно имеет высокую сложность."
            })
            
    except Exception as e:
        # В случае ошибки возвращаем fallback текст
        return JsonResponse({
            'success': True,
            'text': f"ИИ-анализ временно недоступен. Техническая информация: {str(e)}"
        })

@require_POST
def upload_url(request):
    url = request.POST.get('url', '').strip()
    
    if not url:
        return JsonResponse({
            'success': False,
            'message': 'Пожалуйста, введите ссылку на календарь'
        })
    
    try:
        # Здесь вы можете обработать ссылку:
        # 1. Сохранить в базу данных
        # 2. Проанализировать содержимое
        # 3. Создать событие в календаре и т.д.
        
        
        # Пример: просто логируем полученную ссылку
        print(f"Получена ссылка: {url}")

        webcal_url = url.split(":", 1)
        webcal_url = "".join(["https", ":", webcal_url[-1]])
        webcal_text = requests.request("GET", webcal_url).text
        converter = SimpleICSToJSONConverter()
        event_list = converter.parse_ics_content(webcal_text)
        event_storage = EventStorage()
        event_storage.import_events_from_list(event_list)
        
        # Можно добавить в сессию для демонстрации
        
        return JsonResponse({
            'success': True,
            'message': f'Ссылка успешно загружена: {url[:50]}...',
            'should_refresh': False  # Можно установить True, если нужно обновить страницу
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Ошибка при обработке: {str(e)}'
        })
    
@csrf_exempt
def analyze_docx_view(request):
    """Отдельный endpoint для анализа DOCX файлов"""
    return handle_file_analysis(request)