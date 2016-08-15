'use strict'

const normalize = require('normalize-for-search')
const pipe = require('multipipe')
const stations = require('db-stations')
const filter = require('stream-filter')
const map = require('through2-map')
const autocomplete = require('cli-autocomplete')



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

module.exports = where
