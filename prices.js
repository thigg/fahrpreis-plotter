'use strict'

const minimist = require('minimist')
const normalize = require('normalize-for-search')
const pipe = require('multipipe')
const stations = require('db-stations')
const filter = require('stream-filter')
const map = require('through2-map')
const autocomplete = require('cli-autocomplete')
const so = require('so')
const prices = require('db-prices')

const render = require('./render')

const argv = minimist(process.argv.slice(2))



const suggest = (input) => new Promise((yay, nay) => {
	if (!input) return yay([])

	input = normalize(input)
	const match = (station) =>
		normalize(station.name).indexOf(input) >= 0

	const stream = pipe(
		  stations()
		, filter(match, {objectMode: true})
		, map.obj((s) => ({value: s.id, title: s.name}))
	)

	const results = []
	const onResult = (s) => {
		results.push(s)
		if (results.length === 5) {
			stream.end()
			stream.removeListener('data', onResult)
			yay(results)
		}
	}
	stream.once('error', nay)
	stream.on('end', () => yay(results))
	stream.on('data', onResult)
})

const where = (msg) => new Promise((yay, nay) =>
	autocomplete(msg, suggest)
	.once('error', nay)
	.once('submit', yay))



so(function* () {

	const from = /[0-9]+/.test(argv._[0])
		? +argv._[0]
		: yield where('From where?')

	const to = /[0-9]+/.test(argv._[1])
		? +argv._[1]
		: yield where('To where?')

	const now = new Date()
	const days = new Array(argv.days || 7)
		.fill(null, 0, argv.days || 7)
		.map((_, i) => new Date(now.getYear(), now.getMonth(), now.getDate() + i + 1))

	const byDay = yield Promise.all(days
		.map((when) => prices(from, to, when)))
	process.stdout.write(render(byDay) + '\n')
	process.exit()

})()
.catch(console.error)
