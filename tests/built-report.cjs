// The built demo report and the pages it keeps, escaped, inside template elements; shared by the tests that read it.
const fs = require('node:fs');
const path = require('node:path');

const html = fs.readFileSync(path.join(__dirname, '..', 'invoice-insights.html'), 'utf8');
const between = (text, start, end) => {
  const from = text.indexOf(start) + start.length;
  return text.slice(from, text.indexOf(end, from));
};
const unescapeHtml = text => [['&lt;', '<'], ['&gt;', '>'], ['&quot;', '"'], ['&#x27;', "'"], ['&amp;', '&']]
  .reduce((result, [entity, character]) => result.split(entity).join(character), text);
// A page the report keeps inside <template id="…">, unescaped.
const templateSource = id => unescapeHtml(between(html, `<template id="${id}">`, '</template>'));
// The inline scripts of such a page, in order.
const scriptsOf = id => [...templateSource(id).matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].map(match => match[1]);
// A data constant such a page embeds, such as `matchReportData`, read back.
const embedded = (id, name) => JSON.parse(between(templateSource(id), `const ${name} = `, '</script>').trim().replace(/;$/, ''));

module.exports = { html, between, templateSource, scriptsOf, embedded };
