from flask import Flask, render_template, request, redirect, url_for, flash
import requests
import socket
import pickle

app = Flask(__name__)
app.secret_key = "sister-fakestore-client"


# ============================================================
# KONFIGURASI SERVER
# ============================================================

# Ganti dengan IP laptop masing-masing server

# Server 1 - RPC
RPC_SERVER_HOST = "192.168.x.x"
RPC_SERVER_PORT = 6001

# Server 2 - RMI
RMI_SERVER_HOST = "192.168.x.x"
RMI_SERVER_PORT = 6002

# Server 3 - REST API
API_SERVER_HOST = "192.168.x.x"
API_SERVER_PORT = 6003

API_SERVER = f"http://{API_SERVER_HOST}:{API_SERVER_PORT}"


# ============================================================
# FUNGSI KOMUNIKASI SOCKET + PICKLE
# ============================================================

def send_pickle_request(host, port, data):
    """
    Mengirim request menggunakan socket + pickle.

    Digunakan untuk komunikasi:
    Client -> Server 1 (RPC)
    Client -> Server 2 (RMI)
    """

    try:
        client_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        client_socket.settimeout(5)

        # Connect ke server
        client_socket.connect((host, port))

        # Serialize data menggunakan pickle
        message = pickle.dumps(data)

        # Kirim data
        client_socket.sendall(message)

        # Penting:
        # Server 1 dan Server 2 membaca data sampai EOF.
        # Karena itu client harus memberi tanda bahwa
        # pengiriman request sudah selesai.
        client_socket.shutdown(socket.SHUT_WR)

        # Menerima response
        response_data = b""

        while True:
            try:
                chunk = client_socket.recv(4096)

                if not chunk:
                    break

                response_data += chunk

            except socket.timeout:
                break

        client_socket.close()

        if response_data:
            return pickle.loads(response_data)

        return {
            "success": False,
            "message": "Server tidak memberikan response."
        }

    except ConnectionRefusedError:
        return {
            "success": False,
            "message": f"Tidak dapat terhubung ke server {host}:{port}."
        }

    except socket.timeout:
        return {
            "success": False,
            "message": "Koneksi ke server timeout."
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Terjadi kesalahan: {str(e)}"
        }


# ============================================================
# REST API - SERVER 3
# ============================================================

def get_products():
    """
    Mengambil daftar produk dari Server 3.
    Server 3 kemudian mengambil data dari Server 4.
    """

    try:
        response = requests.get(
            f"{API_SERVER}/products",
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()

            # Jika response langsung berupa list
            if isinstance(data, list):
                return data

            # Jika response berupa {"products": [...]}
            if isinstance(data, dict):
                return data.get("products", [])

        return []

    except requests.exceptions.ConnectionError:
        print("Tidak dapat terhubung ke Server 3.")

    except requests.exceptions.Timeout:
        print("Request ke Server 3 timeout.")

    except Exception as e:
        print("Error mengambil produk:", e)

    return []


# ============================================================
# RPC - SERVER 1
# ============================================================

def buy_product(product_id, quantity):
    """
    Meminta Server 1 melakukan transaksi pembelian.

    Alur:
    Client -> Server 1 -> Server 4
    """

    request_data = {
        "method": "buy",
        "params": {
            "product_id": int(product_id),
            "qty": int(quantity)
        }
    }

    return send_pickle_request(
        RPC_SERVER_HOST,
        RPC_SERVER_PORT,
        request_data
    )


# ============================================================
# RMI - SERVER 2
# ============================================================

def check_stock(product_id):
    """
    Meminta Server 2 mengecek stok produk.

    Alur:
    Client -> Server 2 -> Server 4
    """

    request_data = {
        "object": "StockService",
        "method": "get_stock",
        "params": {
            "product_id": int(product_id)
        }
    }

    return send_pickle_request(
        RMI_SERVER_HOST,
        RMI_SERVER_PORT,
        request_data
    )


def update_stock(product_id, quantity):
    """
    Meminta Server 2 melakukan update stok.

    quantity positif  = tambah stok
    quantity negatif  = kurangi stok
    """

    request_data = {
        "object": "StockService",
        "method": "update_stock",
        "params": {
            "product_id": int(product_id),
            "qty": int(quantity)
        }
    }

    return send_pickle_request(
        RMI_SERVER_HOST,
        RMI_SERVER_PORT,
        request_data
    )


# ============================================================
# HALAMAN UTAMA
# ============================================================

@app.route("/")
def index():

    products = get_products()

    return render_template(
        "index.html",
        products=products
    )


# ============================================================
# DETAIL / CEK STOK
# ============================================================

@app.route("/stock/<product_id>")
def stock(product_id):

    result = check_stock(product_id)

    # Server 2 get_stock mengembalikan:
    # {
    #     "product_id": ...,
    #     "name": ...,
    #     "stock": ...
    # }
    #
    # Jika gagal:
    # {
    #     "error": "..."
    # }

    if "error" not in result:

        flash(
            f"Stok {result.get('name', 'produk')}: "
            f"{result.get('stock', 0)}",
            "success"
        )

    else:

        flash(
            result.get(
                "error",
                "Gagal mengecek stok."
            ),
            "error"
        )

    return redirect(url_for("index"))


# ============================================================
# PEMBELIAN PRODUK
# ============================================================

@app.route("/buy", methods=["POST"])
def buy():

    product_id = request.form.get("product_id")
    quantity = request.form.get("quantity")

    # Validasi product ID
    if not product_id:

        flash(
            "Produk tidak ditemukan.",
            "error"
        )

        return redirect(url_for("index"))

    # Validasi jumlah
    try:

        quantity = int(quantity)

        if quantity <= 0:
            raise ValueError

    except (ValueError, TypeError):

        flash(
            "Jumlah pembelian harus berupa angka lebih dari 0.",
            "error"
        )

        return redirect(url_for("index"))

    # Kirim transaksi ke Server 1
    result = buy_product(
        product_id,
        quantity
    )

    if result.get("success"):

        message = result.get(
            "message",
            "Pembelian berhasil."
        )

        flash(
            message,
            "success"
        )

    else:

        message = result.get(
            "message",
            "Pembelian gagal."
        )

        flash(
            message,
            "error"
        )

    return redirect(url_for("index"))


# ============================================================
# UPDATE STOK
# ============================================================

@app.route("/update-stock", methods=["POST"])
def update_stock_route():

    product_id = request.form.get("product_id")
    quantity = request.form.get("quantity")

    if not product_id:

        flash(
            "Produk tidak ditemukan.",
            "error"
        )

        return redirect(url_for("index"))

    try:

        quantity = int(quantity)

    except (ValueError, TypeError):

        flash(
            "Jumlah stok harus berupa angka.",
            "error"
        )

        return redirect(url_for("index"))

    result = update_stock(
        product_id,
        quantity
    )

    if result.get("success"):

        flash(
            result.get(
                "message",
                "Stok berhasil diperbarui."
            ),
            "success"
        )

    else:

        flash(
            result.get(
                "message",
                result.get(
                    "error",
                    "Gagal memperbarui stok."
                )
            ),
            "error"
        )

    return redirect(url_for("index"))


# ============================================================
# HALAMAN STATUS SERVER
# ============================================================

@app.route("/status")
def status():

    server_status = {
        "server1": "Tidak diketahui",
        "server2": "Tidak diketahui",
        "server3": "Tidak diketahui"
    }

    # ----------------------------
    # Cek Server 3
    # ----------------------------

    try:

        response = requests.get(
            f"{API_SERVER}/products",
            timeout=2
        )

        if response.status_code == 200:
            server_status["server3"] = "Aktif"
        else:
            server_status["server3"] = "Error"

    except Exception:

        server_status["server3"] = "Tidak terhubung"


    # ----------------------------
    # Cek Server 1
    # ----------------------------

    try:

        test_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        test_socket.settimeout(2)

        test_socket.connect(
            (
                RPC_SERVER_HOST,
                RPC_SERVER_PORT
            )
        )

        test_socket.close()

        server_status["server1"] = "Aktif"

    except Exception:

        server_status["server1"] = "Tidak terhubung"


    # ----------------------------
    # Cek Server 2
    # ----------------------------

    try:

        test_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        test_socket.settimeout(2)

        test_socket.connect(
            (
                RMI_SERVER_HOST,
                RMI_SERVER_PORT
            )
        )

        test_socket.close()

        server_status["server2"] = "Aktif"

    except Exception:

        server_status["server2"] = "Tidak terhubung"


    return render_template(
        "index.html",
        products=get_products(),
        server_status=server_status
    )


# ============================================================
# MENJALANKAN CLIENT
# ============================================================

if __name__ == "__main__":

    print("=" * 50)
    print("CLIENT TOKO ONLINE")
    print("=" * 50)
    print("Client berjalan pada:")
    print("http://localhost:5000")
    print("=" * 50)

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
