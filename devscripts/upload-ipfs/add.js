// this assumes to be run inside ipfs.yml

const ipfsHttp = require("ipfs-http-client");
const { globSource } = ipfsHttp;

const clients = [
  ipfsHttp("http://127.0.0.1:5001"),
  ipfsHttp("https://ipfs.infura.io:5001"),
  ipfsHttp("https://ipfs.oceanprotocol.com/ipfs/"),
];

async function main() {
  const results = (
    await Promise.all(
      clients
        .map((a) => a.add(globSource("./ytdl-patched", { recursive: true })))
        .map((a) => a.catch(() => false))
    )
  ).filter((a) => a);
  console.log(results);
  const cid = results[0].cid.toString();
  console.log(`::set-output name=ipfs-hash::${cid}`);
}

main()
  .then(() => {})
  .catch((a) => {
    console.log(a);
    process.exit(1);
  });
