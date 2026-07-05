const fs = require('fs');
const path = require('path');
console.log('cwd', process.cwd());
const paths = [
  'node_modules/lightningcss/node/index.js',
  'node_modules/lightningcss/lightningcss.linux-x64-musl.node',
  'node_modules/lightningcss/lightningcss.linux-x64-gnu.node',
  'node_modules/lightningcss-linux-x64-musl/lightningcss.linux-x64-musl.node',
  'node_modules/lightningcss-linux-x64-gnu/lightningcss.linux-x64-gnu.node'
];
for (const p of paths) {
  const abs = path.resolve(p);
  console.log(p, abs, fs.existsSync(abs));
  if (fs.existsSync(abs)) {
    const stat = fs.lstatSync(abs);
    console.log('  symlink', stat.isSymbolicLink());
    if (stat.isSymbolicLink()) console.log('  target', fs.readlinkSync(abs));
  }
}
try {
  console.log('resolve index', require.resolve('lightningcss/node/index.js'));
} catch (err) {
  console.error('resolve failed', err.message);
}
try {
  const lightning = require('lightningcss');
  console.log('loaded', typeof lightning, lightning && lightning.version);
} catch (err) {
  console.error('require failed', err.stack || err.message);
}
