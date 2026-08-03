import os
import json
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

API_KEY = os.environ.get("GEMINI_API_KEY")
RSS_URL = "https://feeds.bbci.co.uk/news/world/rss.xml"

print(f"--- BOT BAŞLATILDI ---")

def get_latest_news():
    try:
        req = urllib.request.Request(RSS_URL, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req).read()
        root = ET.fromstring(html)
        
        items = root.findall('.//item')[:12]
        news_list = []
        for item in items:
            title = item.find('title').text if item.find('title') is not None else ""
            description = item.find('description').text if item.find('description') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            
            # MAGAZİN & EĞLENCE FİLTRESİ
            ignore_keywords = ["concert", "singer", "pop star", "music", "album", "movie", "actor", "actress", "massive attack", "ariana grande"]
            combined_text = (title + " " + description).lower()
            if any(k in combined_text for k in ignore_keywords):
                print(f"Magazin içerik elendi: {title}")
                continue

            news_list.append({"title": title, "text": description, "link": link})
        return news_list
    except Exception as e:
        print(f"RSS Hatası: {e}")
        return []

def analyze_with_gemini(news_item):
    models_to_try = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash"]
    
    prompt = f"""
    Aşağıdaki haberi analiz et. Eğer haber magazin, müzik, spor veya eğlence ile ilgiliyse SADECE "SKIPPED" yaz. 
    Eğer uluslararası siyaset, askeri, diplomasi veya jeopolitik bir haber ise BİREBİR şu JSON formatında Türkçe yanıt ver:

    Başlık: {news_item['title']}
    İçerik: {news_item['text']}

    JSON Şablonu:
    {{
        "title": "Türkçe Başlık",
        "tags": ["#Etiket1", "#Etiket2"],
        "summary": "10 cümlelik detaylı özet.",
        "history": "10 cümlelik tarihsel hafıza analizi.",
        "link": "{news_item['link']}",
        "countries": {{
            "Turkey": {{"role": "Aktör", "color": "#22c55e"}},
            "Ukraine": {{"role": "Aktör", "color": "#ef4444"}}
        }}
    }}
    Ülke isimleri İngilizce standart olsun (Turkey, Russia, Ukraine, Greece, United States, Iran, Pakistan, India vb.).
    """

    data = {"contents": [{"parts": [{"text": prompt}]}]}

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
        
        try:
            response = urllib.request.urlopen(req)
            res_data = json.loads(response.read().decode('utf-8'))
            text_response = res_data['candidates'][0]['content']['parts'][0]['text'].strip()
            
            if "SKIPPED" in text_response:
                return None

            text_response = text_response.replace("```json", "").replace("```", "").strip()
            return json.loads(text_response)
        except Exception:
            continue
            
    return None

def main():
    if not API_KEY:
        print("KRİTİK HATA: GEMINI_API_KEY tanımlı değil!")
        return

    existing_news = []
    if os.path.exists('newsData.json'):
        try:
            with open('newsData.json', 'r', encoding='utf-8') as f:
                existing_news = json.load(f)
        except Exception:
            existing_news = []

    existing_links = {item.get('link') for item in existing_news if 'link' in item}
    raw_news = get_latest_news()
    newly_processed = []

    for idx, item in enumerate(raw_news):
        if item['link'] in existing_links:
            continue

        print(f"Haber İşleniyor: {item['title']}")
        result = analyze_with_gemini(item)
        if result:
            newly_processed.append(result)
        time.sleep(2)

    all_news = newly_processed + existing_news
    for index, item in enumerate(all_news):
        item['id'] = index + 1

    with open('newsData.json', 'w', encoding='utf-8') as f:
        json.dump(all_news, f, ensure_ascii=False, indent=4)
    print("newsData.json güncellendi.")

if __name__ == "__main__":
    main()
