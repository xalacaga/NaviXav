const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../navixav/web/static/app.js'), 'utf8').replaceAll('\r\n', '\n');
function rule(id) {
  const marker = source.indexOf(`id: "${id}"`);
  const start = source.lastIndexOf('\n  {', marker);
  const end = source.indexOf('\n  },', marker) + 4;
  return vm.runInNewContext('(' + source.slice(start, end) + ')', {
    finiteOr: value => value == null ? null : Number(value), STD_PRESSURE_HPA: 1013.25,
  });
}
test('confirmed Fenix STD suppresses the STD reminder despite an old QNH', () => {
  assert.equal(rule('std_not_set').when({ configuration: { altimeter_std: true, altimeter_hpa: 1008 } }), false);
});
test('confirmed QNH suppresses the QNH reminder even at standard pressure', () => {
  assert.equal(rule('qnh_not_set').when({ configuration: { altimeter_std: false, altimeter_hpa: 1013.25 } }), false);
});
test('unavailable Fenix mode and pressure cannot trigger either reminder', () => {
  for (const id of ['std_not_set', 'qnh_not_set']) {
    assert.equal(rule(id).when({ configuration: { altimeter_std: null, altimeter_hpa: null } }), false);
  }
});

test('ILS alarm compares the dedicated receiver even when NAV1 differs', () => {
  const c = {plan:{arrival:{ils_frequency_mhz:108.15}}, configuration:{nav1_frequency_mhz:113.6, ils_frequency_mhz:108.14999999999999}};
  assert.equal(rule('ils_mismatch').when(c), false);
  c.configuration.ils_frequency_mhz = 110.30;
  assert.equal(rule('ils_mismatch').when(c), true);
  c.configuration.ils_frequency_mhz = null;
  assert.equal(rule('ils_mismatch').when(c), false);
  assert.equal(rule('ils_mismatch').armed(c), false);
});
