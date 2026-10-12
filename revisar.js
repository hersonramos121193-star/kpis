// Prueba de la carga en lote. Solo corre con pruebas/mock.py (lo inyecta en la página); nada va a Google.
// Sube todos los .xlsx de la carpeta dos veces y revisa que cada periodo guardado coincida con su archivo
// (faltas, incapacidades, días de incapacidad, incidencias y bajas). La 2a vuelta detecta duplicados.
// Supone que cada archivo trae todos los registros de su periodo (como los de "KPIs por periodo 2026").
async function revisar() {
  store.set('kpis_clave', 'secreta');
  const avisos = [];
  window.confirm = () => true;
  window.alert = m => avisos.push(m);
  const nombres = await (await fetch('/archivos')).json();
  const bufs = await Promise.all(nombres.map(async n => [n, await (await fetch('/archivos/' + encodeURIComponent(n))).arrayBuffer()]));
  const res = [], t0 = Date.now();
  let fallo = false;
  for (const vuelta of [1, 2]) {
    await cargarVarios(bufs.map(([n, b]) => new File([b], n)));
    const dif = [];
    for (const [n, b] of bufs) {
      const d = parse(XLSX.read(b, { cellDates: true }));
      d.periodo = periodoDeFecha(ymd(d.del));
      if (!d.periodo) continue; // cargarVarios ya lo reporta en el aviso
      repartir(d);
      const s = hist.semanal.find(r => r.id_semana === idDe(d.periodo)) || {};
      const esperado = [d.faltas.length, d.incap.length, sum(d.incap, i => diasEnPeriodo(i, d.del, d.al)), d.nom.length, d.bajas.length];
      const guardado = [s.faltas, s.incapacidades, s.dias_incapacidad, s.incidencias_nomina, s.bajas].map(v => Number(v) || 0);
      if (esperado.join() !== guardado.join()) dif.push(`${n}: archivo ${esperado.join('/')} · guardado ${guardado.join('/')}`);
    }
    const aviso = avisos.at(-1) || '';
    if (dif.length || !aviso.startsWith('Listo')) fallo = true;
    res.push(`Vuelta ${vuelta}: ${dif.length ? 'NO COINCIDEN (faltas/incap/días/incidencias/bajas)\n  ' + dif.join('\n  ') : `${bufs.length} archivos coinciden`}\n  Aviso: ${aviso}`);
  }
  const guardados = (await (await fetch('/exec')).json()).guardados;
  const txt = `${fallo ? '✗ FALLA' : '✓ PASA'} · ${guardados} guardados en ${Math.round((Date.now() - t0) / 1000)} s\n` + res.join('\n');
  document.body.insertAdjacentHTML('afterbegin', `<pre id="resultadoPrueba" style="margin:0;padding:12px 16px;background:${fallo ? '#ffd2d2' : '#d8f5d8'};color:#000;white-space:pre-wrap">${esc(txt)}</pre>`);
  console.log(txt);
  return txt;
}
if (location.hash === '#revisar') addEventListener('load', () => setTimeout(revisar, 500)); // deja que cargue el histórico vacío primero
