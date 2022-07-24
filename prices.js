#!/usr/bin/env node
'use strict'

const mri = require('mri')
const so = require('so')
const prices = require('db-prices')

const where = require('./where')
const render = require('./render')
const dbrender = require('./dbrenderer')


const argv = mri(process.argv.slice(2), {
    boolean: ['help', 'h']
})


if (argv.help || argv.h) {
    process.stdout.write(`\
Usage: db-prices [from] [to] [options]

Arguments:
    from            Station number (e.g. 8011160).
    to              Station number (e.g. 8000261).

Options:
    --days      -d  The number of days to show. Default: 7`)
    process.exit(0)
}


(async () => {

    const from = /[0-9]+/.test(argv._[0])
        ? +argv._[0]
        : await where('From where?')

    const to = /[0-9]+/.test(argv._[1])
        ? +argv._[1]
        : await where('To where?')

    const renderer = argv.renderer || "console"

    const now = new Date()
    const days = new Array(argv.days || argv.d || 7)
        .fill(null, 0, argv.days || argv.d || 7)
        .map((_, i) => new Date(now.getFullYear(), now.getMonth(), now.getDate() + i + 1))

    const byDay = await Promise.all(days.map(async (when) => {
        const res = await prices(from, to, when)
        return res.sort((a, b) => a.price.amount - b.price.amount)
    }))
    if (renderer === "console")
        process.stdout.write(render(byDay) + '\n')
    else if (renderer === "db") {
        dbrender(byDay, from, to , argv.destfolder || "./");
        process.stdout.write('wrote to db')
    } else throw 'unknown renderer ' +renderer

})()
    .catch((err) => {
        console.error(err)
        process.exit(1)
    })
