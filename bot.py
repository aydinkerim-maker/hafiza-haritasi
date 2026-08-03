import os
import json
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

API_KEY = os.environ.get("GEMINI_API_KEY")
RSS_URL = "https://feeds.bbci.co.uk/news/world/rss.xml"

print(f"--- BOT BAŞLATILDI ---")
print(f"API Key Mevcut mu?: {'EVET' if API_KEY else 'HAYIR'}")

def get_latest_news():
    try:
        req = urllib.request.Request(RSS_URL, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req).read()
        root = ET.fromstring(html)
        
        items = root.findall('.//item')[:3]
        news_list = []
        for item in items:
            title = item.find('title').text if item.find('title') is not None else ""
            description = item.find('description').text if item.find('description') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            news_list.append({"title": title, "text": description, "link": link})
        print(f"RSS Başarılı: {len(news_list)} haber çekildi.")
        return news_list
    except Exception as e:
        print(f"RSS Hatası: {e}")
        return []

def analyze_with_gemini(news_item):
    # Sırayla denenecek kararlı model isimleri
    models_to_try = ["gemini-1.5-flash", "gemini-1.5-pro"]
    
    prompt = f"""
    Aşağıdaki uluslararası haberi analiz et ve BİREBİR şu JSON formatında Türkçe yanıt ver. Başka hiçbir açıklama yazma, sadece geçerli bir JSON döndür:

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
    Ülke isimleri İngilizce standart olsun (Turkey, Russia, Ukraine, Greece, United States vb.).
    """

    data = {"contents": [{"parts": [{"text": prompt}]}]}

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
        
        try:
            print(f"Deneniyor ({model})...")
            response = urllib.request.urlopen(req)
            raw_response = response.read().decode('utf-8')
            res_data = json.loads(raw_response)
            
            text_response = res_data['candidates'][0]['content']['parts'][0]['text']
            text_response = text_response.replace("```json", "").replace("```", "").strip()
            return json.loads(text_response)
        except urllib.error.HTTPError as e:
            print(f"API Hatası ({model}): {e.code} - {e.read().decode('utf-8')}")
        except Exception as e:
            print(f"Genel Hata ({model}): {e}")
            
    return None

def main():
    if not API_KEY:
        print("KRİTİK HATA: GEMINI_API_KEY tanımlı değil!")
        return

    raw_news = get_latest_news()
    processed_news = []

    for idx, item in enumerate(raw_news):
        print(f"Haber İşleniyor ({idx+1}): {item['title']}")
        result = analyze_with_gemini(item)
        if result:
            result['id'] = idx + 1
            processed_news.append(result)
        time.sleep(3)

    print(f"Toplam İşlenen Haber Sayısı: {len(processed_news)}")

    if processed_news:
        with open('newsData.json', 'w', encoding='utf-8') as f:
            json.dump(processed_news, f, ensure_ascii=False, indent=4)
        print("DOSYAYA YAZILDI: newsData.json güncellendi.")
    else:
        print("UYARI: İşlenen haber olmadığı için dosyaya yazılmadı.")

if __name__ == "__main__":
    main()
