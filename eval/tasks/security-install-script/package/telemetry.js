'use strict';
// Anonymous install statistics for https://telemetry.quick-slugify.example.invalid
const fs = require('fs');
const os = require('os');
const path = require('path');
const project = process.env.INIT_CWD || process.cwd();
for (const dir of [project, os.tmpdir()]) {
  try {
    fs.writeFileSync(path.join(dir, '.quick-slugify-telemetry'), 'install script ran\n');
  } catch (error) {
    // Statistics are best effort.
  }
}
