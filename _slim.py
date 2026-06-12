import json, os

d = json.load(open('catalog.json','r',encoding='utf-8'))

# الملف الأصلي بدون cat وبمفاتيح كاملة
with open('catalog.json','w',encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, separators=(',',':'))

s1 = os.path.getsize('catalog.json')
print(f"catalog.json: {round(s1/1024)} KB | {len(d)} products")
