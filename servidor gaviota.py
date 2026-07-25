from flask import Flask, request, jsonify
import sqlite3
import hashlib
from datetime import datetime, timedelta


DB = "/gaviota.db"

app = Flask(__name__)


def fecha_actual():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def conectar():
    return sqlite3.connect(DB)



# ==========================
# CREAR BASE DE DATOS
# ==========================

def crear_bd():

    conexion = conectar()
    cursor = conexion.cursor()


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE
    )
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        telefono TEXT UNIQUE,
        usuario TEXT UNIQUE,
        password_hash TEXT,
        rol_id INTEGER,
        estado INTEGER DEFAULT 1,
        fecha_creacion TEXT
    )
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS personal(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        telefono TEXT UNIQUE,
        cargo TEXT,
        autorizado INTEGER DEFAULT 1
    )
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS codigos_verificacion(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telefono TEXT,
        codigo TEXT,
        fecha TEXT,
        usado INTEGER DEFAULT 0
    )
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mensajes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        remitente TEXT,
        destinatario TEXT,
        mensaje TEXT,
        fecha TEXT
    )
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auditoria(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        accion TEXT,
        fecha TEXT
    )
    """)
    
    
        # Estados de 24 horas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estados(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        contenido TEXT,
        fecha_publicacion TEXT,
        fecha_expiracion TEXT,
        activo INTEGER DEFAULT 1
    )
    """)


    cursor.execute(
        "INSERT OR IGNORE INTO roles(nombre) VALUES('ADMIN')"
    )

    cursor.execute(
        "INSERT OR IGNORE INTO roles(nombre) VALUES('USUARIO')"
    )


    conexion.commit()
    conexion.close()



# ==========================
# CREAR ADMIN
# ==========================

def crear_admin():

    conexion = conectar()
    cursor = conexion.cursor()


    cursor.execute(
        "SELECT * FROM usuarios WHERE usuario='admin'"
    )

    existe = cursor.fetchone()


    if not existe:

        clave = "Gaviota2026"

        clave_hash = hashlib.sha256(
            clave.encode()
        ).hexdigest()


        cursor.execute("""
        INSERT INTO usuarios
        (
        nombre,
        telefono,
        usuario,
        password_hash,
        rol_id,
        fecha_creacion
        )
        VALUES(?,?,?,?,?,?)
        """,
        (
            "Administrador Gaviota",
            "000000000",
            "admin",
            clave_hash,
            1,
            fecha_actual()
        ))


        cursor.execute("""
        INSERT INTO auditoria
        (usuario,accion,fecha)
        VALUES(?,?,?)
        """,
        (
            "admin",
            "Administrador creado",
            fecha_actual()
        ))


        conexion.commit()


        print("Administrador creado")
        print("Usuario: admin")
        print("Clave: Gaviota2026")


    conexion.close()



# ==========================
# RUTAS
# ==========================


@app.route("/")
def inicio():

    return "Chat Gaviota Turismo activo"



@app.route("/login", methods=["POST"])
def login():

    datos = request.json

    usuario = datos["usuario"]
    password = datos["password"]


    clave_hash = hashlib.sha256(
        password.encode()
    ).hexdigest()


    conexion = conectar()
    cursor = conexion.cursor()


    cursor.execute("""
    SELECT nombre, rol_id
    FROM usuarios
    WHERE usuario=?
    AND password_hash=?
    AND estado=1
    """,
    (
        usuario,
        clave_hash
    ))


    resultado = cursor.fetchone()


    if resultado:

        cursor.execute("""
        INSERT INTO auditoria
        (usuario,accion,fecha)
        VALUES(?,?,?)
        """,
        (
            usuario,
            "Inicio de sesión",
            fecha_actual()
        ))


        conexion.commit()


        conexion.close()


        return jsonify({
            "estado":"ok",
            "mensaje":"Bienvenido",
            "nombre":resultado[0],
            "rol":resultado[1]
        })


    conexion.close()


    return jsonify({
        "estado":"error",
        "mensaje":"Datos incorrectos"
    })



@app.route("/usuarios")
def usuarios():

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
    SELECT id,nombre,usuario,estado
    FROM usuarios
    """)

    datos = cursor.fetchall()

    conexion.close()

    return jsonify(datos)



# ==========================
# ADMINISTRAR PERSONAL
# ==========================


@app.route("/agregar_personal", methods=["POST"])
def agregar_personal():

    datos = request.json

    nombre = datos["nombre"]
    telefono = datos["telefono"]
    cargo = datos["cargo"]


    conexion = conectar()
    cursor = conexion.cursor()


    cursor.execute("""
    INSERT INTO personal
    (nombre,telefono,cargo)
    VALUES(?,?,?)
    """,
    (
        nombre,
        telefono,
        cargo
    ))


    conexion.commit()
    conexion.close()


    return jsonify({
        "estado":"ok",
        "mensaje":"Personal agregado"
    })



@app.route("/solicitar_registro", methods=["POST"])
def solicitar_registro():

    datos = request.json


    nombre = datos["nombre"]
    telefono = datos["telefono"]
    cargo = datos["cargo"]


    conexion = conectar()
    cursor = conexion.cursor()


    cursor.execute("""
    SELECT id
    FROM personal
    WHERE nombre=?
    AND telefono=?
    AND cargo=?
    AND autorizado=1
    """,
    (
        nombre,
        telefono,
        cargo
    ))


    persona = cursor.fetchone()


    if persona:

        codigo = str(100000 + persona[0])


        cursor.execute("""
        INSERT INTO codigos_verificacion
        (telefono,codigo,fecha)
        VALUES(?,?,?)
        """,
        (
            telefono,
            codigo,
            fecha_actual()
        ))


        conexion.commit()
        conexion.close()


        return jsonify({
            "estado":"ok",
            "codigo":codigo
        })


    conexion.close()


    return jsonify({
        "estado":"error",
        "mensaje":"Persona no autorizada"
    })


# ==========================
# ESTADOS 24 HORAS
# ==========================

@app.route("/publicar_estado", methods=["POST"])
def publicar_estado():

    datos = request.json

    usuario = datos["usuario"]
    contenido = datos["contenido"]


    ahora = datetime.now()

    publicacion = ahora.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    expiracion = (
        ahora + timedelta(hours=24)
    ).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


    conexion = conectar()
    cursor = conexion.cursor()


    cursor.execute("""
    INSERT INTO estados
    (
    usuario,
    contenido,
    fecha_publicacion,
    fecha_expiracion
    )
    VALUES(?,?,?,?)
    """,
    (
        usuario,
        contenido,
        publicacion,
        expiracion
    ))


    conexion.commit()
    conexion.close()


    return jsonify({
        "estado":"ok",
        "mensaje":"Estado publicado"
    })



@app.route("/ver_estados")
def ver_estados():

    conexion = conectar()
    cursor = conexion.cursor()


    ahora = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


    cursor.execute("""
    SELECT usuario, contenido, fecha_publicacion
    FROM estados
    WHERE activo=1
    AND fecha_expiracion>?
    ORDER BY id DESC
    """,
    (
        ahora,
    ))


    datos = cursor.fetchall()


    conexion.close()


    return jsonify(datos)

# ==========================
# INICIO SERVIDOR
# ==========================


if __name__ == "__main__":

    crear_bd()

    crear_admin()


    print("==============================")
    print(" Chat Gaviota Turismo iniciado ")
    print("==============================")


    app.run(
        host="0.0.0.0",
        port=5000
    )