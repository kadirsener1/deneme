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

        if eslesmeler := re.findall(referer_deseni, icerik):
            return list(set(eslesmeler))  # Aynı domain birden fazla kez olabilir
        else:
            raise ValueError("M3U dosyasında 'trgoals' içeren referer domain bulunamadı!")

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
            return check_domain(self.redirect_gec(eldeki_domain))
        except Exception:
            konsol.log("[red][!] redirect_gec(eldeki_domain) başarısız.")
            try:
                return check_domain(self.redirect_gec("https://t.co/MTLoNVkGQN"))
            except Exception:
                konsol.log("[red][!] Yedek link başarısız, domain +1 deneniyor...")
                try:
                    rakam = int(eldeki_domain.split("trgoals")[1].split(".")[0]) + 1
                    return f"https://trgoals{rakam}.xyz"
                except:
                    raise ValueError("Yeni domain üretilemedi!")

    def kanal_idlerini_al(self):
        with open(self.m3u_dosyasi, "r") as dosya:
            icerik = dosya.read()
        return list(set(re.findall(r'/channel\.html\?id=([\w\d]+)', icerik)))

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

                yayin_url = f"{yayin_ara[1].rstrip('/')}/{kanal_id}.m3u8"
                konsol.log(f"[green][+] {kanal_id} ➜ {yayin_url}")

                # Eski URL'yi bul ve değiştir
                eski_yayin_url_regex = rf'https?://[^/]+/(?:{kanal_id}\.m3u8)?'
                m3u_icerik = re.sub(eski_yayin_url_regex, yayin_url, m3u_icerik)
                m3u_icerik = m3u_icerik.replace(eldeki_domain, yeni_domain)

        with open(self.m3u_dosyasi, "w") as dosya:
            dosya.write(m3u_icerik)
        konsol.log("[green][✔] M3U güncellemesi tamamlandı.")

if __name__ == "__main__":
    guncelleyici = TRGoals("1.m3u")
    guncelleyici.m3u_guncelle()
