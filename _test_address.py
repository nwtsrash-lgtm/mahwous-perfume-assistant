# -*- coding: utf-8 -*-
from personas_engine import generate_persona

for i in range(5):
    p = generate_persona()
    a = p['address']
    name = p['name']
    city = p['city']
    print(f'=== {name} | {city} ===')
    print(f'  رقم المبنى:     {a["building"]}')
    print(f'  الشارع:         {a["street"]}')
    print(f'  الحي:           {a["district"]}')
    print(f'  المدينة:        {a["city"]}')
    print(f'  الرمز البريدي:  {a["postal"]}')
    print(f'  الرقم الإضافي:  {a["extra"]}')
    print(f'  المختصر:        {a.get("short_code","N/A")}')
    print(f'  الكامل:         {a["full"]}')
    print()
