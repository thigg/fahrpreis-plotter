'use strict'

const readStations = require('db-stations')
const autocompleteDbStations = require('db-stations-autocomplete')
const promptAutocomplete = require('cli-autocomplete')

const pStations = new Promise((resolve, reject) => {
	const res = Object.create(null)
	readStations()
	.on('data', (s) => {
		res[s.id] = s
	})
	.once('end', () => {
		resolve(res)
	})
	.once('error', reject)
})

const suggest = (input) => {
	return pStations
	.then((stationsById) => {
		const results = autocompleteDbStations(input, 5)
		const choices = []

		for (let result of results) {
			const station = stationsById[result.id]
			if (!station) continue

			choices.push({
				title: [
					station.name,
					'–',
					'score:', result.score.toFixed(3),
					'relevance:', result.relevance.toFixed(3)
				].join(' '),
				value: station.id
			})
		}

		return choices
	})
}

const where = (msg) => new Promise((yay, nay) =>
	promptAutocomplete(msg, suggest)
	.once('error', nay)
	.once('submit', yay))

module.exports = where
