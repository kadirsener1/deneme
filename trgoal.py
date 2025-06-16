from Kekik.cli import konsol
from httpx     import Client
from parsel    import Selector
import re

class TRGoals:
    def __init__(self, m3u_dosyasi):
        self.m3u_dosyasi = m3u_dosyasi
        self.httpx = Client(timeout=10, verify=False)
        self.domain = "https://trgoals1351.xyz"

    def referer_domainini_al(self):
        desen = r'#EXTVLCOPT:http-referrer=(https?://[^/]*trgoals[^/]*\.[^\s/]+)'
        with open(self.m3u_dosyasi, "r", encoding="utf-8") as dosya:
            icerik = dosya.read()
        if eslesme := re.search(desen, icerik):
            return eslesme[1]
        raise ValueError("M3U dosyasında 'trgoals' içeren referer domain bulunamadı!")

    def kanal_idlerini_al(self):
        with open(self.m3u_dosyasi, "r", encoding="utf-8") as dosya:
            icerik = dosya.read()
        # Tüm tvg-id değerlerini unique olarak al
        id_listesi = list(set(re.findall(r'tvg-id="([^"]+)"', icerik)))
        if not id_listesi:
            raise ValueError("M3U dosyasında hiç tvg-id bulunamadı!")
        return id_listesi

   def m3u_guncelle(self):
    eldeki_domain = self.referer_domainini_al()
    konsol.log(f"[yellow][~] Bilinen Domain : {eldeki_domain}")

    yeni_domain = self.yeni_domaini_al(eldeki_domain)
    konsol.log(f"[green][+] Yeni Domain    : {yeni_domain}")

    kontrol_url = f"{yeni_domain}/channel.html?id=yayin1"

    with open(self.m3u_dosyasi, "r") as dosya:
        m3u_icerik = dosya.read()

    if not (eski_yayin_url := re.search(r'https?:\/\/[^\/]+\.(workers\.dev|shop|click|lat)\/?', m3u_icerik)):
        raise ValueError("M3U dosyasında eski yayın URL'si bulunamadı!")

    eski_yayin_url = eski_yayin_url[0]
    konsol.log(f"[yellow][~] Eski Yayın URL : {eski_yayin_url}")

    # Kanal id'leri tvg-id'den alalım
    kanal_idler = re.findall(r'tvg-id="(\d+)"', m3u_icerik)
    if not kanal_idler:
        raise ValueError("M3U dosyasında tvg-id bulunamadı!")

    # Sayfayı sadece 1 kez çekiyoruz (tek id ile)
    response = self.httpx.get(kontrol_url, follow_redirects=True)

    if not (yayin_ara := re.search(r'(?:var|let|const)\s+baseurl\s*=\s*"(https?://[^"]+)"', response.text)):
        secici = Selector(response.text)
        baslik = secici.xpath("//title/text()").get()
        if baslik == "404 Not Found":
            yeni_baseurl = eski_yayin_url.rstrip('/')
        else:
            konsol.print(response.text)
            raise ValueError("Base URL bulunamadı!")
    else:
        yeni_baseurl = yayin_ara[1].rstrip('/')

    konsol.log(f"[green][+] Yeni Base URL : {yeni_baseurl}")

    # M3U içeriğinde eski yayın URL'sini yeni baseurl + /kanal_id.m3u8 ile değiştiriyoruz
    yeni_m3u_icerik = m3u_icerik

    for kanal_id in kanal_idler:
        yeni_link = f"{yeni_baseurl}/{kanal_id}.m3u8"
        # eski_yayin_url veya mevcut kanalların linklerini yeni_link ile değiştir
        # Burada sadece eski_yayin_url'yi değiştiriyoruz; farklı linkler varsa onları değiştirmek için ayrı kod gerekebilir
        yeni_m3u_icerik = yeni_m3u_icerik.replace(eski_yayin_url, yeni_link)

    # referer domainlerini de güncelle
    yeni_m3u_icerik = yeni_m3u_icerik.replace(eldeki_domain, yeni_domain)

    with open(self.m3u_dosyasi, "w") as dosya:
        dosya.write(yeni_m3u_icerik)

        konsol.log("[green]✅ Tüm kanallar için M3U dosyası güncellendi.")

if __name__ == "__main__":
    guncelleyici = TRGoals("1.m3u")
    guncelleyici.m3u_guncelle()
