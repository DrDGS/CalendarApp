import requests
from giga import giga
from ICSToJSONConverter import SimpleICSToJSONConverter

url="webcal://lks.bmstu.ru/lks-back/srv/v2/ics/f9821818-8a79-11ec-b81a-0de102063aa5"

converter = SimpleICSToJSONConverter()

def webcal_url_to_jsons(webcal_url):
    webcal_url = webcal_url.split(":", 1)
    webcal_url = "".join(["https", ":", webcal_url[-1]])
    print(webcal_url)
    webcal_text = requests.request("GET", webcal_url).text
    print(webcal_text)
    print(converter.parse_ics_content(webcal_text))

# print(giga.delete_file('c055e9ba-04f8-45c8-8093-dc30eef35a49'))
