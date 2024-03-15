import {createClient} from 'hafas-client'
import {profile as dbProfile} from 'hafas-client/p/db/index.js'
import {DateTime, Duration} from "luxon";

import sqlite3 from 'sqlite3';

const {Database, verbose} = sqlite3;
verbose();

let args_array = process.argv.slice(2)
let args = {"fromName":args_array[0],"toName":args_array[1],"days":args_array[2],"dbFile":args_array[3]}

const userAgent = 'github.com/thigg/fahrpreis-plotter'

const client = createClient(dbProfile, userAgent)

async function getFromTo(from, to) {
    let loc1 = await client.locations(from)
    let loc2 = await client.locations(to)
    let from_id = loc1[0].id;
    let to_id = loc2[0].id;
    return {from_id, to_id};
}

let {from_id, to_id} = await getFromTo(args.fromName, args.toName);

let now = DateTime.now()

async function queryPrices(from, to, now, number_of_days) {
    let all_prices = []
    for (let day_offset = 0; day_offset < number_of_days; day_offset++) {
        let query_day = now.plus(Duration.fromObject({days: day_offset}))
        let prices = await client.bestPrices(from, to, query_day.toJSDate())
        let compact_prices = prices.bestPrices
            .map(d => ({
                "when": d.fromDate,
                "price": d.bestPrice?.amount
            })).filter(d => d.price !== undefined)
        all_prices = all_prices.concat(compact_prices)

    }
    return all_prices;
}

let all_prices = await queryPrices(from_id, to_id, now, args.days);

function persistPrices(from, to, allPrices, queried_at, db_path) {
    let from_int = parseInt(from);
    let to_int = parseInt(to);
    let db = new sqlite3.Database(db_path, (err) => {
        if (err) {
            console.error(err)
            return console.error(err.message);
        }
    });
    db.serialize(() => {

        db.run('BEGIN TRANSACTION');
        db.run(`CREATE TABLE IF NOT EXISTS \`fahrpreise\` (
                  \`id\` integer not null primary key autoincrement,
                  \`from\` INT not null,
                  \`to\` INT not null,
                  \`when\` DATETIME not null,
                  \`price_cents\` INT not null,
                  \`queried_at\` datetime not null
                )`
        )
        const stmt = db.prepare('INSERT INTO fahrpreise (`from`,`to`,`when`,`price_cents`,`queried_at`) VALUES (?,?,?,?,?);');
        for (let data of allPrices) {
            stmt.run(from_int, to_int, new Date(data.when), Math.trunc(data.price * 100), queried_at
            )
        }

        stmt.finalize()

        db.run('COMMIT', (err) => {
            if (err) {
                console.error('Error committing transaction', err);
            } else {
                console.log(`Wrote ${allPrices.length} entries`);
            }
        });
    });
}

persistPrices(from_id, to_id, all_prices, now.toJSDate(), args.dbFile);

