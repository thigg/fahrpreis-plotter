'use strict'

const fs = require('fs');
const zlib = require('zlib');
const { Readable } = require("stream")
const brotli = zlib.createBrotliCompress( { chunkSize: 32 * 1024,
    params: {
    [zlib.constants.BROTLI_PARAM_MODE]: zlib.constants.BROTLI_MODE_TEXT,
        [zlib.constants.BROTLI_PARAM_QUALITY]: 8,
        [zlib.constants.BROTLI_PARAM_SIZE_HINT]: 3461903
}});

const days = (days, from, to, destfolder) => {
    const data = JSON.stringify({queried_at: new Date(), data: days})
    const readable = Readable.from([data])
    let filename = destfolder + Date.now() + "-" + from + "-" + to + '.json.brotli';

    const out = fs.createWriteStream(filename);
    readable.pipe(brotli).pipe(out);
}

module.exports = days
