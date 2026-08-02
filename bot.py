import os
import json
import urllib.request
import xml.etree.ElementTree as ET

# Gemini API Anahtarını GitHub Kasasından Çek
API_KEY = os.environ.get("GEMINI_API_KEY")

# Taranacak RSS Haber Kaynakları (Örn: BBC World News)
RSS_URL = "https://feeds.bbci.co.uk/news/world/rss.xml"

def get_latest_news():
    try:
        req = urllib.request.Request(RSS_URL, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req).read()
        root = ET.fromstring(html)
        
        items = root.findall('.//item')[:3] # İlk 3 güncel haberi al
        news_list = []
        for item in items:
            title = item.find('title').text
            description = item.find('description').text if item.find('description') is not None else ""
            link = item.find('link').text
            news_list.append({"title": title, "text": description, "link": link})
        return news_list
    except Exception as e:
        print(f"RSS Çekme Hatası: {e}")
        return []

def analyze_with_gemini(news_item):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    prompt = f"""
    Aşağıdaki uluslararası haberi analiz et ve BİREBİR şu JSON formatında Türkçe yanıt ver. Başka hiçbir açıklama yazma, sadece JSON dündür:

    Haber: {news_item['title']} - {news_item['text']}

    JSON Şablonu:
    {{
        "title": "Türkçe Çarpıcı Başlık",
        "tags": ["#Etiket1", "#Etiket2", "#ÜlkeAdi"],
        "summary": "En fazla 10 cümlelik detaylı ve tarafsız haber özeti.",
        "history": "En fazla 10 cümlelik olayın geçmişteki kökenleri, anlaşmaları ve tarihsel hafıza analizi.",
        "link": "{news_item['link']}",
        "countries": {{
            "Turkey": {{"role": "Aktör veya Arabulucu veya Destekçi", "color": "#22c55e"}},
            "Ukraine": {{"role": "Aktör veya Arabulucu veya Destekçi", "color": "#ef4444"}}
        }}
    }}
    Ülke kodları İngilizce (Turkey, Russia, Ukraine, Greece vb.) olsun. Renkler: Aktör için #ef4444, Arabulucu için #22c55e, Destekçi için #38bdf8.
    """

    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    
    try:
        response = urllib.request.urlopen(req)
        res_data = json.loads(response.read().decode('utf-8'))
        text_response = res_data['candidates'][0]['content']['parts'][0]['text']
        
        # JSON temizleme
        text_response = text_response.replace("```json", "").replace("```", "").strip()
        return json.loads(text_response)
    except Exception as e:
        print(f"Gemini API Hatası: {e}")
        return None

def main():
    if not API_KEY:
        print("API Key bulunamadı!")
        return

    raw_news = get_latest_news()
    processed_news = []

    for idx, item in enumerate(raw_news):
        print(f"Haber İşleniyor: {item['title']}")
        result = analyze_with_gemini(item)
        if result:
            result['id'] = idx + 1
            processed_news.append(result)

    if processed_news:
        with open('newsData.json', 'w', encoding='utf-8') as f:
            json.dump(processed_news, f, ensure_ascii=False, indent=4)
        print("newsData.json başarıyla güncellendi!")

if __name__ == "__main__":
    main()
