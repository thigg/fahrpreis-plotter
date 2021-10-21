'use strict'

const normalize = require('normalize-for-search')
const stations = require('db-stations')
const filter = require('stream-filter')
const map = require('through2-map')
const autocomplete = require('cli-autocomplete')



const suggest = async (input) => {
	if (!input) return []

	input = normalize(input)

	const results = []
	for await (const s of stations()) {
		if (normalize(s.name).indexOf(input) < 0) continue

		results.push({value: s.id, title: s.name})
		if (results.length === 5) break
	}

	return results
}

const where = (msg) => new Promise((yay, nay) =>
	autocomplete(msg, suggest)
	.once('error', nay)
	.once('submit', yay))

module.exports = where
