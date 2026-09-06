const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

const i18n = fs.readFileSync(path.join(__dirname, '../navixav/web/static/i18n.js'), 'utf8');
const app = fs.readFileSync(path.join(__dirname, '../navixav/web/static/app.js'), 'utf8').replaceAll('\r\n', '\n');
const start = app.indexOf('function plannerText(value) {');
const planner = app.slice(start, app.indexOf('\n}\n', start) + 2);

for (const language of ['fr', 'en', 'de', 'es', 'it', 'pt', 'nl', 'pl']) {
  test(`route warnings preserve identifiers and localize in ${language}`, () => {
    const context = vm.createContext({
      window: {}, localStorage: { getItem: () => language },
      displayLocale: () => language,
    });
    vm.runInContext(i18n, context);
    context.t = context.window.I18N.t;
    context.tf = context.window.I18N.format;
    vm.runInContext(planner, context);
    const warning = context.plannerText('Raccord STAR AMB → ODILO non vérifié.');
    assert.ok(warning.includes('AMB') && warning.includes('ODILO'));
    assert.ok(!warning.includes('{'));
    assert.equal(warning, context.tf('reason_link_unverified', { kind: 'STAR', from: 'AMB', to: 'ODILO' }));
    assert.equal(context.plannerText('aucun raccord publié : transition à confirmer'), context.t('reason_connection_missing'));
    assert.equal(context.plannerText('aucun raccord publié : guidage radar à confirmer'), context.t('reason_vectors_unconfirmed'));
    assert.equal(context.plannerText('Transition MOL1E non publiée pour TEST1.'),
      context.tf('reason_transition_unpublished', { transition: 'MOL1E', procedure: 'TEST1' }));
  });
}
