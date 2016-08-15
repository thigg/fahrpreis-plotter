'use strict'

const Table = require('cli-table2')
const moment = require('moment')

const table = () => new Table({
	chars: {
		top:    '', 'top-mid':    '', 'top-left':    '', 'top-right':    '',
		bottom: '', 'bottom-mid': '', 'bottom-left': '', 'bottom-right': '',
		left:   '', 'left-mid':   '',  mid:          '', 'mid-mid':      '',
		right:  '', 'right-mid':  '',  middle:       ' '
	},
	style: {'padding-left': 1, 'padding-right': 0}
})

const day = (day) => {
	if (!day) return null
	return [
		moment(day.trips[0].start).format('ddd DD'),
		day.offer.price
	]
}

const days = (days) => {
	const t = table()
	days
		.map((d) => d.sort((a, b) => a.offer.price - a.offer.price)[0]) // find cheapest
		.map(day).filter((line) => !!line)
		.forEach((line) => t.push(line))
	return t.toString()
}

module.exports = days
