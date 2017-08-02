#!/usr/bin/env node
'use strict'

const mri = require('mri')
const so = require('so')
const prices = require('db-prices')

const where = require('./where')
const render = require('./render')

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



so(function* () {

	const from = /[0-9]+/.test(argv._[0])
		? +argv._[0]
		: yield where('From where?')

	const to = /[0-9]+/.test(argv._[1])
		? +argv._[1]
		: yield where('To where?')

	const now = new Date()
	const days = new Array(argv.days || argv.d || 7)
		.fill(null, 0, argv.days || argv.d || 7)
		.map((_, i) => new Date(now.getFullYear(), now.getMonth(), now.getDate() + i + 1))

	const byDay = yield Promise.all(days.map((when) =>
		prices(from, to, when).then((results) =>
			results.sort((a, b) => a.offer.price - b.offer.price)[0])
	))
	process.stdout.write(render(byDay) + '\n')
	process.exit()

})()
.catch(console.error)
