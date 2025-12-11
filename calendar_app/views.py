from django.shortcuts import render
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