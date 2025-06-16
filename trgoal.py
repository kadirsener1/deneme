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
        yeni_domain = self.domain
        konsol.log(f"[green][+] Yeni Domain    : {yeni_domain}")

        with open(self.m3u_dosyasi, "r", encoding="utf-8") as dosya:
            m3u_icerik = dosya.read()

        kanal_idleri = self.kanal_idlerini_al()

        for kanal_id in kanal_idleri:
            kontrol_url = f"{yeni_domain}/channel.html?id={kanal_id}"
            response = self.httpx.get(kontrol_url, follow_redirects=True)

            eski_yayin_url = re.search(rf'https?:\/\/[^\/]+\.(workers\.dev|shop|click|lat)\/[^\s"]*{kanal_id}[^\s"]*', m3u_icerik)
            if not eski_yayin_url:
                konsol.log(f"[red][-] M3U dosyasında {kanal_id} için eski yayın URL'si bulunamadı, atlanıyor.")
                continue

            eski_yayin_url = eski_yayin_url[0]
            konsol.log(f"[yellow][~] {kanal_id} için Eski Yayın URL : {eski_yayin_url}")

            yayin_url = None
            yayin_ara = re.search(r'(?:var|let|const)\s+baseurl\s*=\s*"(https?://[^"]+)"', response.text)
            if yayin_ara:
                yayin_url = yayin_ara[1]
            else:
                secici = Selector(response.text)
                baslik = secici.xpath("//title/text()").get()
                if baslik == "404 Not Found":
                    yayin_url = eski_yayin_url
                    yeni_domain = eldeki_domain
                else:
                    konsol.print(response.text)
                    konsol.log(f"[red][!] {kanal_id} için yayın URL'si çözümlenemedi, atlanıyor.")
                    continue

            konsol.log(f"[green][+] {kanal_id} için Yeni Yayın URL : {yayin_url}")

            m3u_icerik = m3u_icerik.replace(eski_yayin_url, yayin_url).replace(eldeki_domain, yeni_domain)

        with open(self.m3u_dosyasi, "w", encoding="utf-8") as dosya:
            dosya.write(m3u_icerik)
        konsol.log("[green]✅ Tüm kanallar için M3U dosyası güncellendi.")

if __name__ == "__main__":
    guncelleyici = TRGoals("1.m3u")
    guncelleyici.m3u_guncelle()
