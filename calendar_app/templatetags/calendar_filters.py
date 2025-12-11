# calendar_app/templatetags/calendar_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Получение элемента из словаря по ключу (для events_by_day)"""
    return dictionary.get(key, [])