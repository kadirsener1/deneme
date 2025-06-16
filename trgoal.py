from Kekik.cli import konsol
from httpx     import Client
from parsel    import Selector
import re

class TRGoals:
    def __init__(self, m3u_dosyasi):
        self.m3u_dosyasi = m3u_dosyasi
        self.httpx       = Client(timeout=10, verify=False)

    def referer_domainini_al(self):
        referer_deseni = r'#EXTVLCOPT:http-referrer=(https?://[^/]*trgoals[^/]*\.[^\s/]+)'
        with open(self.m3u_dosyasi, "r") as dosya:
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

    def m3u_guncelle(self):
        eldeki_domain = self.referer_domainini_al()
        konsol.log(f"[yellow][~] Bilinen Domain : {eldeki_domain}")

        yeni_domain = self.yeni_domaini_al(eldeki_domain)
        konsol.log(f"[green][+] Yeni Domain    : {yeni_domain}")

        with open(self.m3u_dosyasi, "r") as dosya:
            m3u_icerik = dosya.read()

        # Kanal bilgilerini buluyoruz (tvg-id ve o kanala ait tüm satırları)
        kanal_deseni = re.compile(r'(#EXTINF:[^\n]+tvg-id="(\d+)"[^\n]*\n)([^\n]+)')
        yeni_m3u_satirlari = []

        for match in kanal_deseni.finditer(m3u_icerik):
            kanal_blok = match.group(1)   # EXTINF satırı
            kanal_id   = match.group(2)   # tvg-id
            kanal_link = match.group(3)   # mevcut link (eskisi)

            kontrol_url = f"{yeni_domain}/channel.html?id=yayin1"

            # Kanal id'ye göre değil sabit 'yayin1' ile istek yapılıyor. İstersen burayı da çoklu id destekli yapabiliriz.
            response = self.httpx.get(kontrol_url, follow_redirects=True)

            if not (yayin_ara := re.search(r'(?:var|let|const)\s+baseurl\s*=\s*"(https?://[^"]+)"', response.text)):
                secici = Selector(response.text)
                baslik = secici.xpath("//title/text()").get()
                if baslik == "404 Not Found":
                    yeni_yayin_url = kanal_link  # hata varsa mevcut link kalsın
                else:
                    konsol.print(response.text)
                    raise ValueError(f"{kanal_id} için baseurl bulunamadı!")
            else:
                # Bulunan baseurl'in sonuna /kanal_id.m3u8 ekle
                baseurl = yayin_ara[1].rstrip('/')
                yeni_yayin_url = f"{baseurl}/{kanal_id}.m3u8"

            konsol.log(f"[green][+] Kanal ID: {kanal_id} - Yeni Yayın URL: {yeni_yayin_url}")

            # Eski linki yenisiyle değiştir
            yeni_m3u_satirlari.append(f"{kanal_blok}{yeni_yayin_url}")

        # Yeni içeriği oluşturuyoruz (sadece güncellenmiş kanallar)
        yeni_m3u_icerik = "#EXTM3U\n" + "\n".join(yeni_m3u_satirlari)

        with open(self.m3u_dosyasi, "w") as dosya:
            dosya.write(yeni_m3u_icerik)


if __name__ == "__main__":
    guncelleyici = TRGoals("1.m3u")
    guncelleyici.m3u_guncelle()
