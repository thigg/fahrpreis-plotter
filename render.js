'use strict'

const chalk = require('chalk')
const moment = require('moment')
const Table = require('cli-table2')

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
		moment(day.legs[0].departure).format('ddd DD'),
		chalk.bold.cyan(day.price.amount + '€'),
		chalk.gray(day.legs
			.map((leg) => moment(leg.departure).format('hh:mm'))
			.join(' '))
	]
}

const days = (days) => {
	const t = table()
	days
		.map(day).filter((line) => !!line)
		.forEach((line) => t.push(line))
	return t.toString()
}

module.exports = days
