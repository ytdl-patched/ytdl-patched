const axios = require("axios");

module.exports = async (req, res) => {
  const {
    query: { release, filename },
  } = req;
  if (release == "latest") {
    const { data: releases } = await axios("https://api.github.com/repos/nao20010128nao/ytdl-patched/releases");
    const latest = releases[0].id;
    return res.redirect(`/api/release/${latest}/${filename}`);
  }
  let releaseData;
  try {
    // release name
    releaseData = (await axios(`https://api.github.com/repos/nao20010128nao/ytdl-patched/releases/${release}`)).data;
  } catch (e) {
    // release tag
    releaseData = (await axios(`https://api.github.com/repos/nao20010128nao/ytdl-patched/releases/tags/${release}`)).data;
  }
  const assets = releaseData.assets;
  for (const asset of assets) {
    if (asset.name == filename) {
      return res.redirect(asset.browser_download_url);
    }
  }
  res.status(404);
};
