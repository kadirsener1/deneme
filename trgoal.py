from Kekik.cli import konsol
from httpx import Client
from parsel import Selector
import re

class TRGoals:
    def __init__(self, m3u_dosyasi):
        self.m3u_dosyasi = m3u_dosyasi
        self.httpx = Client(timeout=10, verify=False)

    def referer_domainini_al(self):
        referer_deseni = r'#EXTVLCOPT:http-referrer=(https?://[^/]*trgoals[^/]*\.[^\s/]+)'
        with open(self.m3u_dosyasi, "r", encoding="utf-8") as dosya:
            icerik = dosya.read()

        if eslesme := re.search(referer_deseni, icerik):
            return eslesme[1]
        else:
            raise ValueError("M3U dosyasında 'trgoals' içeren referer domain bulunamadı!")

    def trgoals_domaini_al(self):
        redirect_url = "https://bit.ly/m/taraftarium24w"
        deneme = 0
        while "bit.ly" in redirect_url and deneme < 5:
            try:
                redirect_url = self.redirect_gec(redirect_url)
            except Exception as e:
                konsol.log(f"[red][!] redirect_gec hata: {e}")
                break
            deneme += 1

        if "bit.ly" in redirect_url or "error" in redirect_url:
            konsol.log("[yellow][!] 5 denemeden sonra bit.ly çözülemedi, yedek linke geçiliyor...")
            try:
                redirect_url = self.redirect_gec("https://t.co/aOAO1eIsqE")
            except Exception as e:
                raise ValueError(f"Yedek linkten de domain alınamadı: {e}")

        return redirect_url

    def redirect_gec(self, redirect_url: str):
        konsol.log(f"[cyan][~] redirect_gec çağrıldı: {redirect_url}")
        try:
            response = self.httpx.get(redirect_url, follow_redirects=True)
        except Exception as e:
            raise ValueError(f"Redirect sırasında hata oluştu: {e}")

        tum_url_listesi = [str(r.url) for r in response.history] + [str(response.url)]

        for url in tum_url_listesi[::-1]:
            if "trgoals" in url:
                return url.strip("/")

        raise ValueError("Redirect zincirinde 'trgoals' içeren bir link bulunamadı!")

    def yeni_domaini_al(self, eldeki_domain: str) -> str:
        def check_domain(domain: str) -> str:
            if domain == "https://trgoalsgiris.xyz":
                raise ValueError("Yeni domain alınamadı")
            return domain

        try:
            yeni_domain = check_domain(self.redirect_gec(eldeki_domain))
        except Exception:
            konsol.log("[red][!] `redirect_gec(eldeki_domain)` fonksiyonunda hata oluştu.")
            try:
                yeni_domain = check_domain(self.trgoals_domaini_al())
            except Exception:
                konsol.log("[red][!] `trgoals_domaini_al` fonksiyonunda hata oluştu.")
                try:
                    yeni_domain = check_domain(self.redirect_gec("https://t.co/MTLoNVkGQN"))
                except Exception:
                    konsol.log("[red][!] `redirect_gec('https://t.co/MTLoNVkGQN')` fonksiyonunda hata oluştu.")
                    rakam = int(eldeki_domain.split("trgoals")[1].split(".")[0]) + 1
                    yeni_domain = f"https://trgoals{rakam}.xyz"

        return yeni_domain

    def kanal_idlerini_al(self):
        with open(self.m3u_dosyasi, "r", encoding="utf-8") as dosya:
            icerik = dosya.read()

        kanal_idleri = re.findall(r'tvg-id="([^"]+)"', icerik)
        kanal_idleri = list(dict.fromkeys(kanal_idleri))  # Tekil ve sıralı
        return kanal_idleri

    def m3u_guncelle(self):
        eldeki_domain = self.referer_domainini_al()
        konsol.log(f"[yellow][~] Bilinen Domain : {eldeki_domain}")

        yeni_domain = self.yeni_domaini_al(eldeki_domain)
        konsol.log(f"[green][+] Yeni Domain    : {yeni_domain}")

        kanal_idleri = self.kanal_idlerini_al()

        with open(self.m3u_dosyasi, "r", encoding="utf-8") as dosya:
            m3u_icerik = dosya.read()

        for kanal_id in kanal_idleri:
            kontrol_url = f"{yeni_domain}/channel.html?id={kanal_id}"
            konsol.log(f"[cyan][~] Kanal ID {kanal_id} için kontrol ediliyor: {kontrol_url}")

            response = self.httpx.get(kontrol_url, follow_redirects=True)

            yayin_url = None
            if (yayin_ara := re.search(r'(?:var|let|const)\s+baseurl\s*=\s*"(https?://[^"]+)"', response.text)):
                yayin_url = yayin_ara[1]
            else:
                secici = Selector(response.text)
                baslik = secici.xpath("//title/text()").get()
                if baslik == "404 Not Found":
                    konsol.log(f"[yellow][!] Kanal ID {kanal_id} için 404 Not Found, eski link kullanılacak.")
                else:
                    konsol.print(response.text)
                    raise ValueError(f"Kanal ID {kanal_id} için baseurl bulunamadı!")

            if yayin_url is None:
                # Base URL bulunamadıysa eski yayını aynı bırak
                continue

            # M3U içindeki eski yayın URL'si arayıp değiştir
            # Burada eski yayın linki bulunmalı ama farklı linkler olabilir,
            # o yüzden mevcut linklerden ilgili kanalın linkini bulup değiştirmek daha doğru olur.
            # Ancak elimizde kanal-link eşleşmesi yoksa tüm eski domainleri değiştiriyoruz.

            # Eski domainleri güncelle
            m3u_icerik = re.sub(
                rf'https?://[^/\s]+/{kanal_id}\.m3u8',
                f'{yayin_url}/{kanal_id}.m3u8',
                m3u_icerik
            )

            # Domain kısmını de güncelle (ör: trgoals1351.xyz -> trgoalsXXXX.xyz)
            eski_domain_regex = r'https?://([^/\s]+)/'
            eski_domainler = set(re.findall(eski_domain_regex, m3u_icerik))
            for eski_domain in eski_domainler:
                if eski_domain.startswith("trgoals"):
                    m3u_icerik = m3u_icerik.replace(eski_domain, yeni_domain.replace("https://", "").strip("/"))

        with open(self.m3u_dosyasi, "w", encoding="utf-8") as dosya:
            dosya.write(m3u_icerik)

        konsol.log("[green][+] M3U dosyası başarıyla güncellendi!")

if __name__ == "__main__":
    guncelleyici = TRGoals("1.m3u")
    guncelleyici.m3u_guncelle()
