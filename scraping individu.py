
import requests
import pandas as pd
import re
import time

from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin, urlparse

HALAMAN_KATEGORI = "https://katadata.co.id/digital/e-commerce"

ARTIKEL_UTAMA = (
    "https://katadata.co.id/digital/e-commerce/"
    "6abf1f2321669/pajak-seller-dipungut-per-1-oktober-"
    "asosiasi-marketplace-ungkap-potensi-kendala"
)

HEADERS = {"User-Agent": "Mozilla/5.0"}
JUMLAH_MAKSIMAL = 10


def bersihkan(teks):
    return re.sub(r"\s+", " ", teks or "").strip()


def ambil_meta(soup, *selectors):
    for selector in selectors:
        tag = soup.select_one(selector)
        if tag:
            nilai = tag.get("content") or tag.get_text(" ", strip=True)
            if nilai:
                return bersihkan(nilai)
    return ""


def kumpulkan_url():
    response = requests.get(
        HALAMAN_KATEGORI, headers=HEADERS, timeout=20
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    daftar_url = [ARTIKEL_UTAMA]

    for tag in soup.select("a[href]"):
        url = urljoin(HALAMAN_KATEGORI, tag["href"])
        parsed = urlparse(url)

        # Hanya tautan artikel pada kategori e-commerce Katadata.
        if (
            parsed.scheme in ("http", "https")
            and parsed.netloc.endswith("katadata.co.id")
            and parsed.path.startswith("/digital/e-commerce/")
            and parsed.path.rstrip("/") != "/digital/e-commerce"
        ):
            if url not in daftar_url:
                daftar_url.append(url)

        if len(daftar_url) >= JUMLAH_MAKSIMAL:
            break

    return daftar_url[:JUMLAH_MAKSIMAL]


def scraping_artikel(url):
    response = requests.get(
        url, headers=HEADERS, timeout=20
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    judul = ambil_meta(
        soup,
        'meta[property="og:title"]',
        'meta[name="twitter:title"]',
        "h1"
    )

    tanggal = ambil_meta(
        soup,
        'meta[property="article:published_time"]',
        'meta[name="pubdate"]',
        'meta[name="date"]'
    )

    penulis = ambil_meta(
        soup,
        'meta[name="author"]',
        'meta[property="article:author"]'
    )

    deskripsi = ambil_meta(
        soup,
        'meta[property="og:description"]',
        'meta[name="description"]'
    )

    isi = ""
    for selector in [
        '[itemprop="articleBody"]',
        "article",
        ".article-content",
        ".detail-content",
        ".content-article"
    ]:
        elemen = soup.select_one(selector)
        if elemen:
            paragraf = [
                bersihkan(p.get_text(" ", strip=True))
                for p in elemen.select("p")
                if bersihkan(p.get_text(" ", strip=True))
            ]
            if paragraf:
                isi = " ".join(paragraf)
                break

    return {
        "judul": judul,
        "penulis": penulis,
        "tanggal_publikasi": tanggal,
        "deskripsi": deskripsi,
        "isi_artikel": isi,
        "url_sumber": url,
        "waktu_scraping": datetime.now().isoformat(
            timespec="seconds"
        )
    }


def main():
    print("Mengambil daftar artikel Katadata...")

    try:
        urls = kumpulkan_url()
        print("Jumlah URL ditemukan:", len(urls))

    except requests.RequestException as error:
        print("Gagal membuka halaman kategori:", error)
        return

    hasil = []

    for nomor, url in enumerate(urls, start=1):
        print(f"[{nomor}/{len(urls)}] Mengambil artikel...")

        try:
            data = scraping_artikel(url)

            if data["judul"]:
                hasil.append(data)
                print("  Berhasil:", data["judul"])
            else:
                print("  Dilewati: judul tidak ditemukan.")

        except requests.RequestException as error:
            print("  Gagal:", error)

        # Memberi jeda agar permintaan tidak terlalu rapat.
        if nomor < len(urls):
            time.sleep(1.5)

    if not hasil:
        print("Tidak ada artikel yang berhasil diambil.")
        return

    df = pd.DataFrame(hasil)
    df.to_csv(
        "hasil_scraping.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\nSCRAPING SELESAI")
    print("Artikel berhasil diambil:", len(df))
    print("File: hasil_scraping.csv")


if __name__ == "__main__":
    main()
