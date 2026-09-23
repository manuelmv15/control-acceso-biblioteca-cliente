"""Tests del servicio del kiosko (servicio/) y de su cliente en la UI
(ui/servicio.py).

La UI corre con el mismo usuario que el estudiante, así que todo lo que
llega al servicio se trata como entrada no confiable: estos tests cubren
tanto el comportamiento normal (login, registro, sesión, PIN) como los
intentos de pedirle al servicio algo que la UI nunca pediría.

La red se reemplaza por `RedFalsa` (mismo contrato que network/), así que no
hace falta `requests` ni un servidor real.
"""
import os
import socket
import stat
import threading

import core.estado as estado_mod
import core.pin_hash as pin_hash
import pytest
from db.estudiantes import buscar_estudiante_cache, guardar_estudiante_cache, obtener_estudiantes_pendientes
from db.sesiones import obtener_pendientes
from network.errores import CarnetYaRegistrado, ServidorNoDisponible
from servicio import servidor as servidor_mod
from servicio.operaciones import PIN_ADMIN_MAX_INTENTOS, ErrorOperacion, ServicioKiosko
from servicio.servidor import ServidorKiosko, despachar, peer_autorizado
from ui import servicio as cliente

ESTUDIANTE = {
    "carnet": "AB12345",
    "nombre": "Ana Pérez",
    "carrera": "Ingeniería de Sistemas Informáticos",
    "facultad": "Departamento de Ingeniería y Arquitectura",
    "fecha_nacimiento": "2003",
    "sexo": "F",
}


class RedFalsa:
    """`caido`: hay conexión pero GET /estudiantes no contesta (timeout,
    429, 5xx). `oculta`: carnets que el GET no ve pero el POST rechaza con
    409, como cuando otra PC los registra entre la consulta y el alta."""

    def __init__(self, conectado=True, en_servidor=None, acepta=True, caido=False, oculta=None):
        self.conectado = conectado
        self.en_servidor = dict(en_servidor or {})
        self.acepta = acepta
        self.caido = caido
        self.oculta = dict(oculta or {})
        self.consultas = []
        self.registrados = []
        self.actualizados = []

    def hay_conexion(self):
        return self.conectado

    def obtener_estudiante(self, carnet):
        self.consultas.append(carnet)
        if self.caido:
            raise ServidorNoDisponible("HTTP 429")
        return self.en_servidor.get(carnet)

    def registrar_estudiante(self, datos):
        self.registrados.append(datos)
        if datos["carnet"] in self.oculta:
            self.en_servidor[datos["carnet"]] = self.oculta.pop(datos["carnet"])
        if datos["carnet"] in self.en_servidor:
            raise CarnetYaRegistrado(datos["carnet"])
        return self.acepta

    def actualizar_estudiante(self, carnet, datos):
        self.actualizados.append((carnet, datos))
        return self.acepta


@pytest.fixture(autouse=True)
def _estado_limpio():
    estado_mod.set_sesion_inactiva()
    yield
    estado_mod.set_sesion_inactiva()


@pytest.fixture
def pin_rapido(monkeypatch):
    """PBKDF2 con pocas iteraciones: el hash guarda sus iteraciones, así que
    verificar_pin() sigue siendo el código real, solo que más rápido."""
    monkeypatch.setattr(pin_hash, "PBKDF2_ITERACIONES", 1000)
    return pin_hash.generar_hash_pin("4321")


def _servicio(red=None, admin_pin_hash="", syncs=None):
    return ServicioKiosko(
        pc_id="PC-TEST",
        duracion_sesion_ms=3_600_000,
        admin_pin_hash=admin_pin_hash,
        bloquear_atajos=True,
        red=red or RedFalsa(),
        forzar_sync=(lambda: syncs.append(1)) if syncs is not None else (lambda: None),
    )


# ── Búsqueda de estudiantes ─────────────────────────────────────────────


def test_buscar_rechaza_carnet_con_formato_invalido(db_temporal):
    with pytest.raises(ErrorOperacion) as exc:
        _servicio().buscar_estudiante("../../etc")
    assert exc.value.codigo == "carnet_invalido"


def test_buscar_consulta_al_servidor_y_cachea(db_temporal):
    red = RedFalsa(en_servidor={"AB12345": {**ESTUDIANTE, "id": "x", "fecha_registro": "2026-01-01"}})
    srv = _servicio(red)

    est = srv.buscar_estudiante("ab12345")

    assert est == ESTUDIANTE  # solo campos públicos, sin id ni fecha_registro
    assert srv.buscar_estudiante("AB12345") == ESTUDIANTE
    assert red.consultas == ["AB12345"]  # la segunda vez sale de la caché


def test_buscar_sin_conexion_ni_cache_devuelve_none(db_temporal):
    red = RedFalsa(conectado=False)
    assert _servicio(red).buscar_estudiante("AB12345") is None
    assert red.consultas == []


# ── Registro y actualización ────────────────────────────────────────────


def test_registrar_estudiante_nuevo(db_temporal):
    red = RedFalsa()
    resultado = _servicio(red).guardar_estudiante("crear", {**ESTUDIANTE, "carnet": "ab12345"})

    assert resultado == {"estudiante": ESTUDIANTE, "estado": "sincronizado"}
    enviado = red.registrados[0]
    assert enviado["carnet"] == "AB12345" and enviado["id"] and enviado["fecha_registro"]
    assert buscar_estudiante_cache("AB12345")["sincronizado"] == 1


def test_registrar_sin_conexion_queda_pendiente(db_temporal):
    resultado = _servicio(RedFalsa(conectado=False)).guardar_estudiante("crear", ESTUDIANTE)

    assert resultado["estado"] == "pendiente_sin_conexion"
    pendientes = obtener_estudiantes_pendientes()
    assert [(p["carnet"], p["pendiente_modo"]) for p in pendientes] == [("AB12345", "crear")]


def test_registrar_rechazado_por_el_servidor_queda_pendiente(db_temporal):
    resultado = _servicio(RedFalsa(acepta=False)).guardar_estudiante("crear", ESTUDIANTE)
    assert resultado["estado"] == "pendiente_error"
    assert len(obtener_estudiantes_pendientes()) == 1


def test_registrar_carnet_existente_se_rechaza(db_temporal):
    red = RedFalsa(en_servidor={"AB12345": ESTUDIANTE})
    with pytest.raises(ErrorOperacion) as exc:
        _servicio(red).guardar_estudiante("crear", {**ESTUDIANTE, "nombre": "Otra persona"})
    assert exc.value.codigo == "carnet_duplicado"
    assert red.registrados == []


def test_buscar_con_servidor_caido_no_se_toma_como_inexistente(db_temporal):
    with pytest.raises(ErrorOperacion) as exc:
        _servicio(RedFalsa(caido=True)).buscar_estudiante("AB12345")
    assert exc.value.codigo == "servidor_no_disponible"


def test_registrar_con_servidor_caido_no_queda_pendiente(db_temporal):
    """Si no se pudo comprobar que el carnet es nuevo, no se guarda nada:
    dejarlo pendiente terminaba pisando la ficha real del estudiante."""
    red = RedFalsa(caido=True)
    with pytest.raises(ErrorOperacion) as exc:
        _servicio(red).guardar_estudiante("crear", ESTUDIANTE)
    assert exc.value.codigo == "servidor_no_disponible"
    assert red.registrados == []
    assert buscar_estudiante_cache("AB12345") is None


def test_registrar_carnet_dado_de_alta_en_otra_pc_cachea_la_ficha_del_servidor(db_temporal):
    red = RedFalsa(oculta={"AB12345": ESTUDIANTE})
    with pytest.raises(ErrorOperacion) as exc:
        _servicio(red).guardar_estudiante("crear", {**ESTUDIANTE, "nombre": "Otra persona"})
    assert exc.value.codigo == "carnet_duplicado"
    cache = buscar_estudiante_cache("AB12345")
    assert cache["nombre"] == "Ana Pérez" and cache["sincronizado"] == 1


@pytest.mark.parametrize("cambio", [
    {"nombre": ""},
    {"nombre": "x" * 256},
    {"carrera": 123},
    {"fecha_nacimiento": "ayer"},
    {"carnet": "AB123"},
])
def test_registrar_valida_los_datos(db_temporal, cambio):
    with pytest.raises(ErrorOperacion):
        _servicio().guardar_estudiante("crear", {**ESTUDIANTE, **cambio})


def test_actualizar_sin_sesion_activa_se_rechaza(db_temporal):
    guardar_estudiante_cache(ESTUDIANTE)
    red = RedFalsa()
    with pytest.raises(ErrorOperacion) as exc:
        _servicio(red).guardar_estudiante("actualizar", {**ESTUDIANTE, "nombre": "X"})
    assert exc.value.codigo == "sin_permiso"
    assert red.actualizados == []
    assert buscar_estudiante_cache("AB12345")["nombre"] == "Ana Pérez"


def test_actualizar_datos_de_otro_carnet_se_rechaza(db_temporal):
    guardar_estudiante_cache(ESTUDIANTE)
    guardar_estudiante_cache({**ESTUDIANTE, "carnet": "CD67890", "nombre": "Carlos"})
    srv = _servicio()
    srv.abrir_sesion(carnet="AB12345")

    with pytest.raises(ErrorOperacion) as exc:
        srv.guardar_estudiante("actualizar", {**ESTUDIANTE, "carnet": "CD67890", "nombre": "X"})
    assert exc.value.codigo == "sin_permiso"
    assert buscar_estudiante_cache("CD67890")["nombre"] == "Carlos"


def test_actualizar_datos_propios_refresca_el_estado_de_la_sesion(db_temporal):
    guardar_estudiante_cache(ESTUDIANTE)
    syncs = []
    red = RedFalsa()
    srv = _servicio(red, syncs=syncs)
    srv.abrir_sesion(carnet="AB12345")

    resultado = srv.guardar_estudiante("actualizar", {**ESTUDIANTE, "nombre": "Ana María Pérez"})

    assert resultado["estado"] == "sincronizado"
    assert red.actualizados[0][0] == "AB12345"
    assert estado_mod.get_estado()["nombre"] == "Ana María Pérez"
    assert syncs


# ── Sesiones ────────────────────────────────────────────────────────────


def test_abrir_sesion_usa_los_datos_de_la_cache_y_el_pc_id_del_servicio(db_temporal):
    guardar_estudiante_cache(ESTUDIANTE)

    sesion = _servicio().abrir_sesion(carnet="AB12345")

    assert sesion["estudiante"] == ESTUDIANTE
    assert sesion["duracion_sesion_ms"] == 3_600_000
    estado = estado_mod.get_estado()
    assert estado["activa"] and estado["carnet"] == "AB12345" and estado["nombre"] == "Ana Pérez"
    assert estado["hora_inicio"] == sesion["hora_inicio"]


def test_abrir_sesion_con_carnet_no_registrado_se_rechaza(db_temporal):
    with pytest.raises(ErrorOperacion) as exc:
        _servicio().abrir_sesion(carnet="AB12345")
    assert exc.value.codigo == "carnet_no_encontrado"
    assert not estado_mod.get_estado()["activa"]


@pytest.mark.parametrize("args", [{}, {"carnet": "AB12345", "sector": "Docente"}, {"sector": ""}])
def test_abrir_sesion_exige_carnet_o_sector(db_temporal, args):
    guardar_estudiante_cache(ESTUDIANTE)
    with pytest.raises(ErrorOperacion):
        _servicio().abrir_sesion(**args)


def test_sesion_de_invitado(db_temporal):
    sesion = _servicio().abrir_sesion(sector="Docente")

    assert sesion["estudiante"] is None
    estado = estado_mod.get_estado()
    assert estado["activa"] and estado["carnet"] is None and estado["nombre"] == "Docente"


def test_abrir_sesion_fuerza_un_heartbeat(db_temporal):
    # El servidor solo deja editar los datos del estudiante con sesión activa
    # en la PC, y se entera por el heartbeat: no puede esperar al intervalo.
    guardar_estudiante_cache(ESTUDIANTE)
    syncs = []
    _servicio(syncs=syncs).abrir_sesion(carnet="AB12345")
    assert syncs


def test_cerrar_sesion_registra_hora_fin_y_sincroniza(db_temporal):
    guardar_estudiante_cache(ESTUDIANTE)
    syncs = []
    srv = _servicio(syncs=syncs)
    sesion = srv.abrir_sesion(carnet="AB12345")
    assert obtener_pendientes() == []  # en curso: todavía no se sincroniza
    syncs.clear()

    assert srv.cerrar_sesion() == {"cerrada": True}

    pendientes = obtener_pendientes()
    assert [p["id"] for p in pendientes] == [sesion["sesion_id"]]
    assert pendientes[0]["pc_id"] == "PC-TEST" and pendientes[0]["hora_fin"]
    assert not estado_mod.get_estado()["activa"]
    assert syncs
    assert srv.cerrar_sesion() == {"cerrada": False}


def test_abrir_sesion_cierra_la_anterior(db_temporal):
    guardar_estudiante_cache(ESTUDIANTE)
    srv = _servicio()
    primera = srv.abrir_sesion(carnet="AB12345")

    segunda = srv.abrir_sesion(sector="Visitante")

    assert [p["id"] for p in obtener_pendientes()] == [primera["sesion_id"]]
    assert segunda["sesion_id"] != primera["sesion_id"]


# ── PIN de administrador ────────────────────────────────────────────────


def test_pin_correcto(db_temporal, pin_rapido):
    srv = _servicio(admin_pin_hash=pin_rapido)
    assert srv.estado_pin_admin() == {"estado": "disponible"}
    assert srv.verificar_pin_admin("4321") == {"estado": "ok"}


def test_pin_se_bloquea_tras_varios_intentos_fallidos(db_temporal, pin_rapido):
    srv = _servicio(admin_pin_hash=pin_rapido)
    for intento in range(1, PIN_ADMIN_MAX_INTENTOS):
        assert srv.verificar_pin_admin("0000")["intentos"] == intento

    assert srv.verificar_pin_admin("0000")["estado"] == "bloqueado"
    # Ni el PIN correcto ni otra instancia del servicio (reinicio) lo desbloquean.
    assert srv.verificar_pin_admin("4321")["estado"] == "bloqueado"
    assert _servicio(admin_pin_hash=pin_rapido).estado_pin_admin()["estado"] == "bloqueado"


def test_pin_sin_configurar_o_legacy(db_temporal):
    assert _servicio(admin_pin_hash="").verificar_pin_admin("1234") == {"estado": "sin_pin"}
    legacy = _servicio(admin_pin_hash="03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4")
    assert legacy.verificar_pin_admin("1234") == {"estado": "legacy"}


# ── Despacho de operaciones ─────────────────────────────────────────────


@pytest.mark.parametrize("peticion,error", [
    ({"op": "get_connection"}, "op_desconocida"),
    ({"op": "_cerrar_sesion_activa"}, "op_desconocida"),
    ({"op": "buscar_estudiante"}, "args_invalidos"),
    ({"op": "buscar_estudiante", "args": {"carnet": "AB12345", "sql": "x"}}, "args_invalidos"),
    ({"op": "info", "args": []}, "args_invalidos"),
    ({"op": "buscar_estudiante", "args": {"carnet": 5}}, "carnet_invalido"),
])
def test_despachar_rechaza_peticiones_no_previstas(db_temporal, peticion, error):
    respuesta = despachar(_servicio(), peticion)
    assert respuesta["ok"] is False and respuesta["error"] == error


def test_despachar_oculta_errores_internos(db_temporal):
    class Roto(RedFalsa):
        def hay_conexion(self):
            raise RuntimeError("detalle interno")

    respuesta = despachar(_servicio(Roto()), {"op": "buscar_estudiante", "args": {"carnet": "AB12345"}})
    assert respuesta == {"ok": False, "error": "error_interno", "mensaje": "error interno del servicio"}


def test_peer_autorizado():
    assert peer_autorizado(os.geteuid(), os.getegid(), "")
    otro_uid = os.geteuid() + 12345
    assert not peer_autorizado(otro_uid, otro_uid, "")
    assert not peer_autorizado(otro_uid, otro_uid, "grupo-que-no-existe-kiosko")


# ── Socket de extremo a extremo ─────────────────────────────────────────


@pytest.fixture
def servidor_en_marcha(db_temporal, tmp_path, monkeypatch):
    ruta = tmp_path / "k.sock"
    monkeypatch.setenv("BIBLIOTECA_SOCKET", str(ruta))
    guardar_estudiante_cache(ESTUDIANTE)
    srv = ServidorKiosko(ruta, _servicio(), grupo_ui="")
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def test_ui_habla_con_el_servicio_por_el_socket(servidor_en_marcha):
    assert cliente.llamar("info") == {"bloquear_atajos": True, "duracion_sesion_ms": 3_600_000}
    assert cliente.llamar("buscar_estudiante", carnet="AB12345") == ESTUDIANTE
    with pytest.raises(cliente.ErrorServicio) as exc:
        cliente.llamar("abrir_sesion", carnet="ZZ99999")
    assert exc.value.codigo == "carnet_no_encontrado"


def test_socket_no_es_accesible_para_otros_usuarios(servidor_en_marcha):
    modo = stat.S_IMODE(servidor_en_marcha.ruta.stat().st_mode)
    assert modo & 0o007 == 0


def test_peer_no_autorizado_no_recibe_respuesta(servidor_en_marcha, monkeypatch):
    monkeypatch.setattr(servidor_mod, "peer_autorizado", lambda *a: False)
    with pytest.raises(cliente.ServicioNoDisponible):
        cliente.llamar("info")


def test_peticion_demasiado_grande_se_rechaza(servidor_en_marcha):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(str(servidor_en_marcha.ruta))
        s.sendall(b"x" * (70 * 1024) + b"\n")
        respuesta = s.makefile("rb").readline()
    assert b"peticion_invalida" in respuesta


def test_no_arranca_si_ya_hay_un_servicio_escuchando(servidor_en_marcha):
    with pytest.raises(RuntimeError):
        ServidorKiosko(servidor_en_marcha.ruta, _servicio(), grupo_ui="")


def test_reemplaza_un_socket_abandonado(db_temporal, tmp_path):
    ruta = tmp_path / "k.sock"
    viejo = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    viejo.bind(str(ruta))
    viejo.close()  # el archivo queda, pero nadie escucha

    srv = ServidorKiosko(ruta, _servicio(), grupo_ui="")
    srv.server_close()
    assert not ruta.exists()


def test_servicio_caido(tmp_path, monkeypatch):
    monkeypatch.setenv("BIBLIOTECA_SOCKET", str(tmp_path / "no-existe.sock"))
    with pytest.raises(cliente.ServicioNoDisponible):
        cliente.llamar("info")
