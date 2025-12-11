from django.shortcuts import render, redirect
from datetime import datetime, date
import calendar
from django.utils import timezone
from .json_storage import event_storage

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
    
    # Создаем объект календаря
    cal = calendar.Calendar(firstweekday=0)  # 0 = понедельник, 6 = воскресенье
    
    # Получаем дни месяца в виде матрицы (список списков)
    month_days = cal.monthdayscalendar(year, month)
    
    # Названия месяцев на русском
    month_names = [
        'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ]
    
    # Названия дней недели на русском
    weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    
    # Подсчитываем количество дней в месяце
    days_in_month = calendar.monthrange(year, month)[1]
    
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
    
    # Получаем события для текущего месяца
    events = event_storage.get_events_by_month(year, month)
    
    # Создаем словарь событий по дням для удобного доступа в шаблоне
    events_by_day = {}
    for event in events:
        event_date = event['date']
        # Извлекаем день из даты (формат YYYY-MM-DD)
        day = int(event_date.split('-')[2])
        if day not in events_by_day:
            events_by_day[day] = []
        events_by_day[day].append(event)
    
    # Создаем список для легкого доступа в шаблоне
    events_list_for_template = []
    for day_num, day_events in events_by_day.items():
        events_list_for_template.append({
            'day': day_num,
            'events': day_events
        })
    
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
        'days_in_month': days_in_month,
        'events_by_day': events_by_day,
        'events_list': events_list_for_template,
        'all_events': events,
    }
    
    return render(request, 'calendar_app/calendar.html', context)


def add_event_view(request):
    """Страница добавления нового события"""
    if request.method == 'POST':
        # Получаем данные из формы
        name = request.POST.get('name', '').strip()
        subject = request.POST.get('subject', '').strip()
        difficulty = request.POST.get('difficulty', '5')
        time_required = request.POST.get('time_required', '5')
        date = request.POST.get('date', '')
        
        # Валидация данных
        if not name or not subject or not date:
            # Можно добавить сообщение об ошибке
            return render(request, 'calendar_app/add_event.html', {
                'error': 'Все поля обязательны для заполнения',
                'form_data': request.POST
            })
        
        try:
            # Преобразуем в числа
            difficulty_int = int(difficulty)
            time_int = int(time_required)
            
            # Проверяем диапазоны
            if not (1 <= difficulty_int <= 10) or not (1 <= time_int <= 10):
                return render(request, 'calendar_app/add_event.html', {
                    'error': 'Сложность и временязатратность должны быть от 1 до 10',
                    'form_data': request.POST
                })
            
            # Создаем объект события
            new_event = {
                'name': name,
                'subject': subject,
                'difficulty': difficulty_int,
                'time_required': time_int,
                'date': date,
                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Добавляем событие через storage
            # Сначала получим все события
            all_events = event_storage.get_all_events()
            
            # Определяем новый ID
            if all_events:
                new_id = max(event.get('id', 0) for event in all_events) + 1
            else:
                new_id = 1
            
            new_event['id'] = new_id
            
            # Добавляем новое событие в список
            all_events.append(new_event)
            
            # Сохраняем обновленный список
            # Нужно создать метод save_all_events в EventStorage или обновить текущий
            # Для простоты создадим временное решение
            
            # Временно: перезаписываем файл напрямую
            import json
            import os
            from django.conf import settings
            
            events_file = os.path.join(settings.BASE_DIR, 'calendar_app', 'events.json')
            with open(events_file, 'w', encoding='utf-8') as f:
                json.dump(all_events, f, ensure_ascii=False, indent=2)
            
            # Перенаправляем на календарь
            return redirect('calendar_app:calendar')
            
        except ValueError:
            return render(request, 'calendar_app/add_event.html', {
                'error': 'Некорректные данные в числовых полях',
                'form_data': request.POST
            })
    
    # GET запрос - показываем пустую форму
    # Если передана дата в параметрах, подставляем её
    selected_date = request.GET.get('date', '')
    return render(request, 'calendar_app/add_event.html', {
        'selected_date': selected_date,
        'today': timezone.localtime(timezone.now()).date().strftime("%Y-%m-%d")
    })