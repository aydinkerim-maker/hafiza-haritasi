import os
import json
import urllib.request
import xml.etree.ElementTree as ET

API_KEY = os.environ.get("GEMINI_API_KEY")
RSS_URL = "https://feeds.bbci.co.uk/news/world/rss.xml"

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
        print(f"RSS'ten {len(news_list)} adet haber çekildi.")
        return news_list
    except Exception as e:
        print(f"RSS Çekme Hatası: {e}")
        return []

def analyze_with_gemini(news_item):
    # En güncel v1beta / gemini-1.5-flash endpoint kullanımı
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    
    prompt = f"""
    Aşağıdaki uluslararası haberi analiz et ve BİREBİR şu JSON formatında Türkçe yanıt ver. Başka hiçbir açıklama, giriş veya çıkış cümlesi yazma. Sadece geçerli bir JSON döndür:

    Haber Başlığı: {news_item['title']}
    Haber İçeriği: {news_item['text']}

    İstenen JSON Formatı:
    {{
        "title": "Türkçe Çarpıcı Başlık",
        "tags": ["#Etiket1", "#Etiket2", "#ÜlkeAdi"],
        "summary": "En fazla 10 cümlelik detaylı ve tarafsız haber özeti.",
        "history": "En fazla 10 cümlelik olayın geçmişteki kökenleri, anlaşmaları ve tarihsel hafıza analizi.",
        "link": "{news_item['link']}",
        "countries": {{
            "Turkey": {{"role": "Aktör", "color": "#22c55e"}},
            "Ukraine": {{"role": "Aktör", "color": "#ef4444"}}
        }}
    }}
    Ülke anahtarları kesinlikle İngilizce standart ismi olsun (Turkey, Russia, Ukraine, Greece, United States vb.). 
    Renkler: Aktör için #ef4444, Arabulucu için #22c55e, Destekçi için #38bdf8.
    """

    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    
    try:
        response = urllib.request.urlopen(req)
        res_data = json.loads(response.read().decode('utf-8'))
        text_response = res_data['candidates'][0]['content']['parts'][0]['text']
        
        # Markdown kod bloklarını temizle
        text_response = text_response.replace("```json", "").replace("```", "").strip()
        return json.loads(text_response)
    except Exception as e:
        print(f"Gemini API Analiz Hatası ({news_item['title']}): {e}")
        return None

def main():
    if not API_KEY:
        print("HATA: GEMINI_API_KEY bulunamadı! Lütfen Secrets alanını kontrol edin.")
        return

    raw_news = get_latest_news()
    processed_news = []

    for idx, item in enumerate(raw_news):
        print(f"İşleniyor ({idx+1}/{len(raw_news)}): {item['title']}")
        result = analyze_with_gemini(item)
        if result:
            result['id'] = idx + 1
            processed_news.append(result)

    if processed_news:
        with open('newsData.json', 'w', encoding='utf-8') as f:
            json.dump(processed_news, f, ensure_ascii=False, indent=4)
        print("BAŞARILI: newsData.json dosyası yeni verilerle dolduruldu!")
    else:
        print("UYARI: Hiçbir haber işlenemedi, newsData.json güncellenmedi.")

if __name__ == "__main__":
    main()
