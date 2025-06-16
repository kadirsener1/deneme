import requests
import re
from time import sleep

# 🔍 Otomatik olarak çalışan en güncel trgoals domainini bul
def find_active_domain():
    base = "https://trgoals{}.xyz"
    for i in range(1351, 1400):  # Domain aralığını gerekirse genişlet
        domain = base.format(i)
        try:
            resp = requests.get(domain, timeout=5)
            if resp.status_code == 200:
                print(f"[+] Aktif domain bulundu: {domain}")
                return domain
        except requests.exceptions.RequestException:
            continue
    raise Exception("Aktif trgoals domaini bulunamadı.")

# 🌐 Kanal ID'den m3u8 linki al (güncellenmiş)
def extract_m3u8(domain, kanal_id):
    url = f"{domain}/channel.html?id={kanal_id}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": domain
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            # iframe src'yi bul
            iframe_match = re.search(r'<iframe[^>]+src="([^"]+)"', r.text)
            if iframe_match:
                iframe_url = iframe_match.group(1)
                if iframe_url.startswith("/"):
                    iframe_url = domain + iframe_url
                elif not iframe_url.startswith("http"):
                    iframe_url = f"{domain}/{iframe_url}"

                r2 = requests.get(iframe_url, headers=headers, timeout=10)
                m3u8_match = re.search(r'(https:\/\/[^"\']+\.m3u8[^"\']*)', r2.text)
                if m3u8_match:
                    found = m3u8_match.group(1)
                    print(f"[✓] {kanal_id} bulundu: {found}")
                    return f"#EXTINF:-1,{kanal_id}\n{found}"
                else:
                    print(f"[!] {kanal_id} iframe içinde m3u8 bulunamadı.")
            else:
                print(f"[!] {kanal_id} için iframe bulunamadı.")
        else:
            print(f"[!] {kanal_id} için HTTP hata: {r.status_code}")
    except Exception as e:
        print(f"[!] {kanal_id} için hata: {e}")
    return None

# 📝 M3U dosyasına yaz
def write_to_m3u(lines, filename="1.m3u"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for line in lines:
            f.write(line + "\n")

if __name__ == "__main__":
    kanal_id_listesi = [
        "yayinzirve", "yayinb2", "yayinb3", "yayinb4", "yayinb5"
        # Buraya diğer ID'leri ekle
    ]

    aktif_domain = find_active_domain()
    m3u_lines = []

    for kid in kanal_id_listesi:
        entry = extract_m3u8(aktif_domain, kid)
        if entry:
            m3u_lines.append(entry)
        sleep(1)  # Sunucuyu yormamak için

    write_to_m3u(m3u_lines)
    print(f"\n[✔] İşlem tamamlandı. 1.m3u dosyasına yazıldı.")
