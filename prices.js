'use strict'

const minimist = require('minimist')
const prices = require('db-prices')

const render = require('./render')

const argv = minimist(process.argv.slice(2))



const now = new Date()
const days = new Array(argv.days || 7)
	.fill(null, 0, argv.days || 7)
	.map((_, i) => new Date(now.getYear(), now.getMonth(), now.getDate() + i + 1))

Promise.all(days.map((when) => prices(argv._[0], argv._[1], when)))
.then((days) => {
	process.stdout.write(render(days) + '\n')
}, console.error)
.catch(console.error)
