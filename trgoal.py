from Kekik.cli import konsol
from httpx import Client
from parsel import Selector
import re

class TRGoals:
    def __init__(self, m3u_dosyasi):
        self.m3u_dosyasi = m3u_dosyasi
        self.httpx = Client(timeout=10, verify=False)

    def referer_domainini_al(self):
        desen = r'#EXTVLCOPT:http-referrer=(https?://[^/]*trgoals[^/]*\.[^\s/]+)'
        with open(self.m3u_dosyasi, "r") as dosya:
            icerik = dosya.read()
        if eslesme := re.search(desen, icerik):
            return eslesme[1]
        raise ValueError("M3U dosyasında trgoals içeren referer bulunamadı!")

    def redirect_gec(self, url: str) -> str:
        konsol.log(f"[cyan][~] Redirect ediliyor: {url}")
        try:
            response = self.httpx.get(url, follow_redirects=True)
        except Exception as e:
            raise ValueError(f"Redirect sırasında hata: {e}")

        tum_url_listesi = [str(r.url) for r in response.history] + [str(response.url)]
        for url in reversed(tum_url_listesi):
            if "trgoals" in url:
                return url.strip("/")
        raise ValueError("Redirect zincirinde trgoals içeren link bulunamadı!")

    def yeni_domaini_al(self, eldeki_domain: str) -> str:
        try:
            return self.redirect_gec(eldeki_domain)
        except Exception:
            konsol.log("[yellow][!] redirect başarısız, trgoals domaini elle arttırılıyor...")
            try:
                rakam = int(re.search(r"trgoals(\d+)", eldeki_domain).group(1)) + 1
                return f"https://trgoals{rakam}.xyz"
            except:
                raise ValueError("Domain otomatik türetilemedi")

    def m3u_guncelle(self):
        eldeki_domain = self.referer_domainini_al()
        konsol.log(f"[yellow][~] Bilinen Domain : {eldeki_domain}")

        yeni_domain = self.yeni_domaini_al(eldeki_domain)
        konsol.log(f"[green][+] Yeni Domain    : {yeni_domain}")

        with open(self.m3u_dosyasi, "r") as dosya:
            m3u_icerik = dosya.read()

        kanal_id_liste = list(set(re.findall(r'id=([a-zA-Z0-9_]+)', m3u_icerik))) or ["yayin1"]

        if not (eski_url := re.search(r'https?:\/\/[^\/]+\.(workers\.dev|shop|click|lat)[^\s"\n]*', m3u_icerik)):
            raise ValueError("Eski yayın URL'si bulunamadı!")
        eski_yayin_url = eski_url[0]
        konsol.log(f"[yellow][~] Eski Yayın URL : {eski_yayin_url}")

        for kanal_id in kanal_id_liste:
            kontrol_url = f"{yeni_domain}/channel.html?id={kanal_id}"
            konsol.log(f"[blue][~] Kontrol ediliyor: {kontrol_url}")

            response = self.httpx.get(kontrol_url, follow_redirects=True)

            if not (yayin_ara := re.search(r'(?:var|let|const)\s+baseurl\s*=\s*"(https?://[^"]+)"', response.text)):
                secici = Selector(response.text)
                if secici.xpath("//title/text()").get() == "404 Not Found":
                    yayin_ara = [None, eski_yayin_url]
                else:
                    konsol.print(response.text)
                    raise ValueError(f"{kanal_id} için baseurl bulunamadı!")

            yayin_url = f"{yayin_ara[1].rstrip('/')}/{kanal_id}.m3u8"
            konsol.log(f"[green][+] Yeni Yayın URL : {yayin_url}")

            # Aynı eski URL'yi kullanan tüm id'leri güncelle
m3u_icerik = re.sub(
    rf'({re.escape(eski_yayin_url.rstrip("/"))}/?{kanal_id}?.m3u8)',
    yayin_url,
    m3u_icerik
)


            m3u_icerik = m3u_icerik.replace(eldeki_domain, yeni_domain)

        with open(self.m3u_dosyasi, "w") as dosya:
            dosya.write(m3u_icerik)

if __name__ == "__main__":
    TRGoals("1.m3u").m3u_guncelle()
