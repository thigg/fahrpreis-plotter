import {createClient} from 'hafas-client'
import {profile as dbProfile} from 'hafas-client/p/db/index.js'
import {DateTime, Duration} from "luxon";

import sqlite3 from 'sqlite3';

const {Database, verbose} = sqlite3;
verbose();


async function getFromTo(from, to) {
    let loc1 = await client.locations(from)
    let loc2 = await client.locations(to)
    let from_id = loc1[0].id;
    let to_id = loc2[0].id;
    return {from_id, to_id};
}


async function queryPrices(from, to, now, number_of_days) {
    let all_prices = []
    for (let day_offset = 0; day_offset < number_of_days; day_offset++) {
        let query_day = now.plus(Duration.fromObject({days: day_offset}))
        let prices = await client.bestPrices(from, to, query_day.toJSDate())
        if (!prices.bestPrices)
            continue
        let compact_prices = prices.bestPrices
            .filter(d => d && d.journeys && d.journeys.length > 0)
            .flatMap(d=>d.journeys)
            .map(journey => ({
                "when": journey.legs[0].plannedDeparture,
                "price": journey.price?.amount,
                "duration": new Date(journey.legs[journey.legs.length - 1].plannedArrival) - new Date(journey.legs[0].plannedDeparture)
            })).filter(d => d.price !== undefined)
        all_prices = all_prices.concat(compact_prices)

    }
    return all_prices;
}


function persist_station(db, station_id, station_name) {
    const check_station_stmt = db.prepare("Select 1 from `stations` where `number` = ? and `name` = ?;");
    const insert_station_stmt = db.prepare("insert into `stations` (`number`,`name`) values (?,?);");
    check_station_stmt.get([station_id, station_name], function (err, row) {
        if (err) {
            console.error(err)
            return console.error(err.message);
        }
        if (!row) {
            insert_station_stmt.run(station_id, station_name)
        }
    });
}

function persistPrices(db, from, to, allPrices, queried_at) {
    let from_int = parseInt(from);
    let to_int = parseInt(to);

    db.serialize(() => {

        /* duckdb schema
        CREATE SEQUENCE id_sequence START 1;
CREATE TABLE "fahrpreise" (
                  "id" integer not null primary key DEFAULT nextval('id_sequence'),
                  "from" INT not null,
                  "to" INT not null,
                  "when" LONG not null,
                  "price_cents" INT not null,
                  "queried_at" LONG not null
                , "travel_duration" INT not null DEFAULT -1);

         */
        db.run('BEGIN TRANSACTION');
        db.run(`CREATE TABLE IF NOT EXISTS \`fahrpreise\` (
                  \`id\` integer not null primary key autoincrement,
                  \`from\` INT not null,
                  \`to\` INT not null,
                  \`when\` DATETIME not null,
                  \`price_cents\` INT not null,
                  \`queried_at\` datetime not null,
                  \`travel_duration\` INT not null DEFAULT -1
                )`
        )
        const stmt = db.prepare('INSERT INTO fahrpreise (`from`,`to`,`when`,`price_cents`,`queried_at`,`travel_duration`) VALUES (?,?,?,?,?,?);');
        for (let data of allPrices) {
            stmt.run(
                from_int, to_int, new Date(data.when), Math.trunc(data.price * 100), queried_at, data.duration
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

let args_array = process.argv.slice(2)
let args = {"fromName": args_array[0], "toName": args_array[1], "days": args_array[2], "dbFile": args_array[3]}

const userAgent = 'github.com/thigg/fahrpreis-plotter'

const client = createClient(dbProfile, userAgent)

let db = new sqlite3.Database(args.dbFile, (err) => {
    if (err) {
        console.error(err)
        return console.error(err.message);
    }
});
let {from_id, to_id} = await getFromTo(args.fromName, args.toName);

let now = DateTime.now()
db.run(`CREATE TABLE IF NOT EXISTS \`stations\` (
                  \`id\` integer not null primary key autoincrement,
                  \`number\` INT not null,
                  \`name\` TEXT not null
                )`
)
persist_station(db, from_id, args.fromName)
persist_station(db, to_id, args.toName)

let all_prices = await queryPrices(from_id, to_id, now, args.days);
persistPrices(db, from_id, to_id, all_prices, now.toJSDate());

