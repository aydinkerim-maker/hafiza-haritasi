import os
import json
import time
import requests
import xml.etree.ElementTree as ET

API_KEY = os.environ.get("GEMINI_API_KEY")

RSS_URLS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml"
]

print("--- BOT BAŞLATILDI (GEMINI 3.5 LITE / 3.6 FLASH) ---", flush=True)

def get_latest_news():
    news_list = []
    ignore_keywords = ["concert", "singer", "pop star", "music", "album", "movie", "actor", "actress", "massive attack", "ariana grande", "sport", "football"]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    for url in RSS_URLS:
        try:
            print(f"RSS Çekiliyor: {url}", flush=True)
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                items = root.findall('.//item')[:5]
                for item in items:
                    title = item.find('title').text if item.find('title') is not None else ""
                    description = item.find('description').text if item.find('description') is not None else ""
                    link = item.find('link').text if item.find('link') is not None else ""
                    
                    combined_text = (title + " " + description).lower()
                    if any(k in combined_text for k in ignore_keywords):
                        continue

                    news_list.append({"title": title, "text": description, "link": link})
            else:
                print(f"RSS Yanıt Vermedi ({response.status_code}): {url}", flush=True)
        except Exception as e:
            print(f"RSS Hatası ({url}): {e}", flush=True)

    return news_list

def analyze_with_gemini(news_item):
    models_to_try = ["gemini-3.5-flash-lite", "gemini-3.6-flash"]
    
    prompt = f"""
    Aşağıdaki haberi analiz et. Eğer haber magazin, müzik, spor veya eğlence ile ilgiliyse SADECE "SKIPPED" yaz. 
    Eğer uluslararası siyaset, askeri, diplomasi veya jeopolitik bir haber ise BİREBİR şu JSON formatında Türkçe yanıt ver:

    Başlık: {news_item['title']}
    İçerik: {news_item['text']}

    JSON Şablonu:
    {{
        "title": "Türkçe Başlık",
        "tags": ["#Etiket1", "#Türkiye", "#ABD", "#İran"],
        "summary": "10 cümlelik detaylı özet.",
        "history": "10 cümlelik tarihsel hafıza analizi.",
        "link": "{news_item['link']}",
        "countries": {{
            "Turkey": {{"role": "Arabulucu (Krizi çözmek için diplomatik görüşme yürütüyor)", "color": "#22c55e"}},
            "United States": {{"role": "Aktör (Bölgeye uçak gemisi sevk eden taraf)", "color": "#38bdf8"}}
        }}
    }}

    KURALLAR:
    1. "tags" kısmına olaya dahil olan ülkelerin TÜRKÇE isimlerini KESİNLİKLE hashtag olarak ekle (Örn: #İran, #ABD, #Rusya). Etiketlerin hepsi Türkçe olmalı.
    2. "role" kısmına sadece "Aktör" veya "Gözlemci" yazıp geçme. Ülkenin o olaydaki rolünü ve ne yaptığını parantez içinde ya da kısaca açıkla (Örn: "Destekçi (Silah yardımı yapıyor)").
    3. JSON içindeki anahtar ülke isimleri (key) mutlaka İngilizce standart kalsın (Turkey, Russia, Ukraine, Greece, United States, Iran, Pakistan, India vb.).
    """

    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
        
        for attempt in range(2):
            try:
                res = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=40)
                if res.status_code == 200:
                    res_data = res.json()
                    text_response = res_data['candidates'][0]['content']['parts'][0]['text'].strip()
                    
                    if "SKIPPED" in text_response:
                        return None

                    text_response = text_response.replace("```json", "").replace("```", "").strip()
                    return json.loads(text_response)
                elif res.status_code in [429, 503]:
                    print(f"Model {model} geçici yoğunluk/kota aldı ({res.status_code}). 10sn bekleniyor...", flush=True)
                    time.sleep(10)
                else:
                    print(f"Model {model} HTTP Hatası: {res.status_code}", flush=True)
                    break
            except Exception as err:
                print(f"Model {model} Bağlantı Uyarısı: {err}", flush=True)
                break
            
    return None

def main():
    if not API_KEY:
        print("KRİTİK HATA: GEMINI_API_KEY tanımlı değil!", flush=True)
        return

    existing_news = []
    if os.path.exists('newsData.json'):
        try:
            with open('newsData.json', 'r', encoding='utf-8') as f:
                existing_news = json.load(f)
        except Exception:
            existing_news = []

    existing_links = {item.get('link') for item in existing_news if 'link' in item}
    existing_titles = {item.get('title', '').lower()[:30] for item in existing_news if 'title' in item}

    raw_news = get_latest_news()
    newly_processed = []

    print(f"Toplam {len(raw_news)} RSS haberi tarandı.", flush=True)

    processed_count = 0
    max_news_per_run = 4 

    for idx, item in enumerate(raw_news):
        if processed_count >= max_news_per_run:
            print(f"Bu tur için maksimum haber limitine ({max_news_per_run}) ulaşıldı.", flush=True)
            break

        clean_title = item['title'].lower()[:30]
        if item['link'] in existing_links or clean_title in existing_titles:
            print(f"Aynı haber geçildi ({idx+1}/{len(raw_news)}): {item['title'][:40]}...", flush=True)
            continue

        print(f"Yeni Haber İşleniyor ({processed_count+1}/{max_news_per_run}): {item['title']}", flush=True)
        result = analyze_with_gemini(item)
        if result:
            newly_processed.append(result)
            existing_titles.add(clean_title)
            processed_count += 1
            print(" -> Başarıyla eklendi.", flush=True)
        
        time.sleep(5)

    all_news = newly_processed + existing_news
    for index, item in enumerate(all_news):
        item['id'] = index + 1

    with open('newsData.json', 'w', encoding='utf-8') as f:
        json.dump(all_news, f, ensure_ascii=False, indent=4)
    print("İşlem tamamlandı. newsData.json güncellendi.", flush=True)

if __name__ == "__main__":
    main()
