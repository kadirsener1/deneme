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
        with open(self.m3u_dosyasi, "r") as dosya:
            icerik = dosya.read()

        refererler = list(set(re.findall(referer_deseni, icerik)))
        if not refererler:
            raise ValueError("M3U dosyasında 'trgoals' içeren referer domain bulunamadı!")
        return refererler

    def kanal_idlerini_al(self):
        with open(self.m3u_dosyasi, "r") as dosya:
            icerik = dosya.read()
        return list(set(re.findall(r'https?://[^\s]+/([a-zA-Z0-9_]+)\.m3u8', icerik)))

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
        eldeki_domainler = self.referer_domainini_al()
        kanal_id_listesi = self.kanal_idlerini_al()

        with open(self.m3u_dosyasi, "r") as dosya:
            m3u_icerik = dosya.read()

        for eldeki_domain in eldeki_domainler:
            yeni_domain = self.yeni_domaini_al(eldeki_domain)
            konsol.log(f"[yellow][~] {eldeki_domain} ➜ [green]{yeni_domain}")

            for kanal_id in kanal_id_listesi:
                kontrol_url = f"{yeni_domain}/channel.html?id={kanal_id}"

                try:
                    response = self.httpx.get(kontrol_url, follow_redirects=True)
                except Exception as e:
                    konsol.log(f"[red][!] {kanal_id} erişim hatası: {e}")
                    continue

                yayin_ara = re.search(r'(?:var|let|const)\s+baseurl\s*=\s*"(https?://[^"]+)"', response.text)
                if not yayin_ara:
                    secici = Selector(response.text)
                    baslik = secici.xpath("//title/text()").get()
                    if baslik == "404 Not Found":
                        konsol.log(f"[red][!] {kanal_id} sayfa 404")
                        continue
                    konsol.log(f"[red][!] {kanal_id} için yayın URL'si bulunamadı!")
                    continue

                yeni_yayin_url = f"{yayin_ara[1].rstrip('/')}/{kanal_id}.m3u8"
                konsol.log(f"[green][+] {kanal_id} ➜ {yeni_yayin_url}")

                kanal_regex = rf'(#EXTINF[^\n]+\n#EXTVLCOPT:http-referrer={re.escape(eldeki_domain)}\n)(https?://[^\s]+{kanal_id}\.m3u8[^\n]*)'
                m3u_icerik = re.sub(kanal_regex, rf'\1{yeni_yayin_url}', m3u_icerik)

            m3u_icerik = m3u_icerik.replace(eldeki_domain, yeni_domain)

        with open(self.m3u_dosyasi, "w") as dosya:
            dosya.write(m3u_icerik)

        konsol.log("[green][✔] M3U güncellemesi tamamlandı.")

if __name__ == "__main__":
    guncelleyici = TRGoals("1.m3u")
    guncelleyici.m3u_guncelle()
