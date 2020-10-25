// start ipfs daemon and wait for "Daemon is.ready"
const childProcess = require("child_process");
const readline = require("readline");

const proc = childProcess.spawn("ipfs", ["daemon"], {
  detached: true,
  stdio: "pipe",
});

proc.stdout.pipe(process.stdout);
proc.stderr.pipe(process.stdout);

const rl = readline.createInterface({
  input: proc.stdout,
});

rl.on("line", (line) => {
  if (line == "Daemon is ready") {
    proc.unref();
    process.exit(0);
  }
});
