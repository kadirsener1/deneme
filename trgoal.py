name: M3U Çekici

on:
  workflow_dispatch:
  schedule:
    - cron: '0 */4 * * *'  # 4 saatte bir çalışır

jobs:
  run-script:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Python kurulumu
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Gereksinimleri yükle
        run: pip install requests

      - name: Scripti çalıştır
        run: python trgoal.py

      - name: M3U dosyasını kaydet
        run: |
          git config --global user.email "kadirsener1@gmail.com"
          git config --global user.name "kadirsener1"
          git add 1.m3u
          git commit -m "M3U güncellendi"
          git push || true
