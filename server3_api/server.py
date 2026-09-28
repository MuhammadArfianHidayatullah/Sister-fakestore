# ============================================================
# SERVER 3 — REST API Server
# Mata Kuliah: Sistem Terdistribusi (IF2228)
# Port: 6003
#
# Tugas:
# - Menyediakan REST API untuk Client
# - Mengambil data produk dari Server 4
# - Client TIDAK mengakses Server 4 secara langsung
#
# Alur:
# Client -> Server 3 -> Server 4
# ============================================================

from flask import Flask, jsonify
import requests


app = Flask(__name__)


# ============================================================
# KONFIGURASI SERVER 4
# ============================================================

# Ganti IP ini dengan IP laptop yang menjalankan Server 4.
SERVER4_HOST = "192.168.1.14"
SERVER4_PORT = 6004

SERVER4_URL = f"http://{SERVER4_HOST}:{SERVER4_PORT}"


# Timeout komunikasi Server 3 -> Server 4
REQUEST_TIMEOUT = 5


# ============================================================
# GET SEMUA PRODUK
# ============================================================

@app.route("/products", methods=["GET"])
def get_products():
    """
    Mengambil semua produk dari Server 4.

    Flow:

    Client
        |
        | GET /products
        v
    Server 3
        |
        | GET /internal/products
        v
    Server 4
        |
        | JSON products
        v
    Server 3
        |
        | JSON products
        v
    Client
    """

    try:
        response = requests.get(
            f"{SERVER4_URL}/internal/products",
            timeout=REQUEST_TIMEOUT
        )

    except requests.exceptions.Timeout:
        return jsonify({
            "error": "Server 4 timeout",
            "message": "Server 4 tidak memberikan response dalam waktu yang ditentukan."
        }), 504

    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": "Server 4 tidak dapat dihubungi",
            "message": "Pastikan Server 4 sedang berjalan dan IP/port sudah benar."
        }), 503

    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": "Gagal menghubungi Server 4",
            "message": str(e)
        }), 502

    # --------------------------------------------------------
    # Jika Server 4 mengembalikan error HTTP
    # --------------------------------------------------------

    if response.status_code != 200:
        try:
            error_data = response.json()
        except ValueError:
            error_data = {
                "message": response.text
            }

        return jsonify({
            "error": "Server 4 mengembalikan error",
            "server4_status": response.status_code,
            "details": error_data
        }), 502

    # --------------------------------------------------------
    # Parse JSON dari Server 4
    # --------------------------------------------------------

    try:
        data = response.json()

    except ValueError:
        return jsonify({
            "error": "Response Server 4 bukan JSON yang valid"
        }), 502

    # --------------------------------------------------------
    # Validasi response
    # --------------------------------------------------------

    if not isinstance(data, dict):
        return jsonify({
            "error": "Format response Server 4 tidak valid"
        }), 502

    if "products" not in data:
        return jsonify({
            "error": "Response Server 4 tidak memiliki field 'products'"
        }), 502

    # --------------------------------------------------------
    # Response ke Client
    # Format sesuai ARCHITECTURE.md:
    #
    # {
    #     "products": [...]
    # }
    # --------------------------------------------------------

    return jsonify({
        "products": data["products"]
    }), 200


# ============================================================
# GET PRODUK BERDASARKAN ID
# ============================================================

@app.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """
    Mengambil satu produk berdasarkan ID.

    Flow:

    Client
        |
        | GET /products/1
        v
    Server 3
        |
        | GET /internal/products/1
        v
    Server 4
        |
        | JSON product
        v
    Server 3
        |
        | JSON product
        v
    Client
    """

    try:
        response = requests.get(
            f"{SERVER4_URL}/internal/products/{product_id}",
            timeout=REQUEST_TIMEOUT
        )

    except requests.exceptions.Timeout:
        return jsonify({
            "error": "Server 4 timeout",
            "message": "Server 4 tidak memberikan response dalam waktu yang ditentukan."
        }), 504

    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": "Server 4 tidak dapat dihubungi",
            "message": "Pastikan Server 4 sedang berjalan dan IP/port sudah benar."
        }), 503

    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": "Gagal menghubungi Server 4",
            "message": str(e)
        }), 502

    # --------------------------------------------------------
    # Produk tidak ditemukan
    # Server 4 menggunakan HTTP 404
    # --------------------------------------------------------

    if response.status_code == 404:
        try:
            error_data = response.json()
        except ValueError:
            error_data = {
                "error": "Produk tidak ditemukan"
            }

        return jsonify(error_data), 404

    # --------------------------------------------------------
    # Error lain dari Server 4
    # --------------------------------------------------------

    if response.status_code != 200:
        try:
            error_data = response.json()
        except ValueError:
            error_data = {
                "message": response.text
            }

        return jsonify({
            "error": "Server 4 mengembalikan error",
            "server4_status": response.status_code,
            "details": error_data
        }), 502

    # --------------------------------------------------------
    # Parse JSON
    # --------------------------------------------------------

    try:
        product = response.json()

    except ValueError:
        return jsonify({
            "error": "Response Server 4 bukan JSON yang valid"
        }), 502

    # --------------------------------------------------------
    # Validasi response
    # --------------------------------------------------------

    if not isinstance(product, dict):
        return jsonify({
            "error": "Format data produk tidak valid"
        }), 502

    # --------------------------------------------------------
    # Response produk
    # --------------------------------------------------------

    return jsonify(product), 200


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health", methods=["GET"])
def health():
    """
    Mengecek apakah Server 3 hidup.

    Endpoint ini tidak bergantung pada Server 4.
    """

    return jsonify({
        "status": "ok",
        "server": "Server 3 - REST API",
        "port": 6003
    }), 200


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("  SERVER 3 — REST API SERVER")
    print("=" * 60)
    print("  Server 3 : http://0.0.0.0:6003")
    print(f"  Server 4 : {SERVER4_URL}")
    print("=" * 60)

    app.run(
        host="0.0.0.0",
        port=6003,
        debug=True,
        threaded=True
    )
