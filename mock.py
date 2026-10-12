"""Servidor de prueba: imita el Apps Script en memoria (nada va a Google) y sirve el dashboard apuntando a él.

Uso:  python pruebas/mock.py "C:/ruta/KPIs por periodo 2026"
      abre http://127.0.0.1:8766/#revisar  (corre pruebas/revisar.js con los .xlsx de esa carpeta)
La clave de prueba es "secreta". Cada vez que se arranca empieza vacío.
"""
import http.server, json, os, re, sys, urllib.parse

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVOS = sys.argv[1] if len(sys.argv) > 1 else '.'
H = {'semanal': [], 'plantas': [], 'rotacion': []}   # lo que devuelve el GET (totales)
D = {}                                                # detalle por id_semana
GUARDADOS = [0]


class Hd(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=RAIZ, **k)

    def log_message(self, *a):
        pass

    def send(self, body, tipo='application/json'):
        b = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(200)
        self.send_header('Content-Type', tipo)
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        ruta = urllib.parse.unquote(self.path.split('?')[0])
        if ruta == '/exec':
            return self.send({'version': 'mock', 'guardados': GUARDADOS[0], **H})
        if ruta in ('/', '/index.html'):
            html = open(os.path.join(RAIZ, 'index.html'), encoding='utf-8').read()
            html = re.sub(r"^const SHEETS_URL = .*$", "const SHEETS_URL = '/exec';", html, count=1, flags=re.M)
            html = html.replace('</body>', '<script src="/pruebas/revisar.js"></script>\n</body>')
            return self.send(html.encode(), 'text/html; charset=utf-8')
        if ruta == '/archivos':
            return self.send(sorted(f for f in os.listdir(ARCHIVOS) if f.endswith('.xlsx') and not f.startswith('~$')))
        if ruta.startswith('/archivos/'):
            return self.send(open(os.path.join(ARCHIVOS, os.path.basename(ruta)), 'rb').read(), 'application/octet-stream')
        return super().do_GET()

    def do_POST(self):  # mismo contrato que apps-script/Codigo.gs
        b = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if b.get('clave') != 'secreta':
            return self.send({'ok': False, 'error': 'Clave incorrecta'})
        i = b['id_semana']
        if b.get('accion') == 'detalle':
            return self.send({'ok': True, **D.get(i, {'faltas': [], 'incapacidades': [], 'incidencias': [], 'bajas': []})})
        t = b['tablas']
        for hoja, clave in (('Historico_Semanal', 'semanal'), ('Historico_Plantas', 'plantas'), ('Rotacion', 'rotacion')):
            H[clave] = [r for r in H[clave] if r['id_semana'] != i] + t.get(hoja, [])
        D[i] = {'faltas': t.get('Faltas', []), 'incapacidades': t.get('Incapacidades', []),
                'incidencias': t.get('Incidencias_Nomina', []), 'bajas': t.get('Bajas', [])}
        GUARDADOS[0] += 1
        self.send({'ok': True})


if __name__ == '__main__':
    print(f'Dashboard de prueba: http://127.0.0.1:8766/#revisar  (archivos: {os.path.abspath(ARCHIVOS)})', flush=True)
    http.server.ThreadingHTTPServer(('127.0.0.1', 8766), Hd).serve_forever()
