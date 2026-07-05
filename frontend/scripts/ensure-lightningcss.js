const fs = require('fs');
const path = require('path');

const projectRoot = path.resolve(__dirname, '..');
const nodeModulesDir = path.join(projectRoot, 'node_modules');
const packageDir = path.join(nodeModulesDir, 'lightningcss');
const nodeDir = path.join(packageDir, 'node');
const gnuBinary = path.join(nodeModulesDir, 'lightningcss-linux-x64-gnu', 'lightningcss.linux-x64-gnu.node');
const muslBinary = path.join(nodeModulesDir, 'lightningcss-linux-x64-musl', 'lightningcss.linux-x64-musl.node');

const packageBindings = [
  { linkPath: path.join(nodeDir, 'lightningcss.linux-x64-gnu.node'), targetPath: gnuBinary },
  { linkPath: path.join(nodeDir, 'lightningcss.linux-x64-musl.node'), targetPath: muslBinary, fallbackTargets: [gnuBinary] },
  { linkPath: path.join(packageDir, 'lightningcss.linux-x64-gnu.node'), targetPath: gnuBinary },
  { linkPath: path.join(packageDir, 'lightningcss.linux-x64-musl.node'), targetPath: muslBinary, fallbackTargets: [gnuBinary] },
  { linkPath: path.join(nodeModulesDir, 'lightningcss.linux-x64-gnu.node'), targetPath: gnuBinary },
  { linkPath: path.join(nodeModulesDir, 'lightningcss.linux-x64-musl.node'), targetPath: muslBinary, fallbackTargets: [gnuBinary] },
];

function resolveTargetPath(targetPath, fallbackTargets = []) {
  if (fs.existsSync(targetPath)) {
    return targetPath;
  }

  for (const fallbackTarget of fallbackTargets) {
    if (fs.existsSync(fallbackTarget)) {
      return fallbackTarget;
    }
  }

  return null;
}

function ensureBinding(linkPath, targetPath, fallbackTargets = []) {
  const resolvedTarget = resolveTargetPath(targetPath, fallbackTargets);
  if (!resolvedTarget) {
    console.warn(`Lightning CSS binary not found at ${targetPath} or any fallback target`);
    return;
  }

  try {
    fs.unlinkSync(linkPath);
  } catch (err) {
    // ignore missing file or link
  }

  fs.mkdirSync(path.dirname(linkPath), { recursive: true });
  fs.copyFileSync(resolvedTarget, linkPath);
  console.log(`Copied ${path.relative(projectRoot, linkPath)} <- ${path.relative(projectRoot, resolvedTarget)}`);
}

if (process.platform === 'linux' && process.arch === 'x64') {
  packageBindings.forEach(({ linkPath, targetPath, fallbackTargets }) => ensureBinding(linkPath, targetPath, fallbackTargets));
} else {
  console.log('Skipping Lightning CSS binding fix for non-Linux x64 runtime');
}
