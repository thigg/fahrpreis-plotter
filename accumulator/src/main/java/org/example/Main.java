package org.example;

import java.io.ByteArrayInputStream;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.EnumSet;
import java.util.List;
import java.util.Set;

import com.jayway.jsonpath.Configuration;
import com.jayway.jsonpath.JsonPath;
import com.jayway.jsonpath.Option;
import com.jayway.jsonpath.spi.json.JacksonJsonProvider;
import com.jayway.jsonpath.spi.json.JsonProvider;
import com.jayway.jsonpath.spi.mapper.JacksonMappingProvider;
import com.jayway.jsonpath.spi.mapper.MappingProvider;
import com.nixxcode.jvmbrotli.common.BrotliLoader;
import com.nixxcode.jvmbrotli.dec.BrotliInputStream;
import lombok.extern.slf4j.Slf4j;
import org.apache.beam.runners.flink.FlinkPipelineOptions;
import org.apache.beam.runners.flink.FlinkRunner;
import org.apache.beam.sdk.Pipeline;
import org.apache.beam.sdk.coders.StringUtf8Coder;
import org.apache.beam.sdk.io.Compression;
import org.apache.beam.sdk.io.FileIO;
import org.apache.beam.sdk.io.jdbc.JdbcIO;
import org.apache.beam.sdk.options.PipelineOptionsFactory;
import org.apache.beam.sdk.transforms.Contextful;
import org.apache.beam.sdk.transforms.FlatMapElements;
import org.apache.beam.sdk.values.PCollection;
import org.apache.beam.sdk.values.TypeDescriptor;

import static org.apache.beam.sdk.io.FileIO.Write.defaultNaming;

@Slf4j
public class Main {
    static final DateTimeFormatter dateTimeFormatter =
            DateTimeFormatter.ISO_INSTANT.withZone(ZoneId.systemDefault());
    public static final JsonPath PRICE_PATH = JsonPath.compile("$.data.*.*.price.amount");
    public static final JsonPath START_TIME_PATH = JsonPath.compile("$.data.*.*.legs[0].departure");
    public static final JsonPath END_TIME_PATH = JsonPath.compile("$.data.*.*.legs[-1].departure");

    public static void main(String[] args) {
        setupTools();
        FlinkPipelineOptions options = PipelineOptionsFactory.create().as(FlinkPipelineOptions.class);
        options.setRunner(FlinkRunner.class);
        options.setFasterCopy(true);
        Pipeline p = Pipeline.create(options);
        //todo map datetime

        final PCollection<PriceQuery> extractedDataPoints = p.apply(FileIO.match().filepattern("/tmp/fahrpreise/*" +
                        ".brotli"))
                .apply(FileIO.readMatches().withCompression(Compression.UNCOMPRESSED))
                .apply(FlatMapElements
                        // uses imports from TypeDescriptors
                        .into(
                                new TypeDescriptor<PriceQuery>() {
                                }
                        )
                        .via(Main::getPriceQueries));
        //writeToDB(extractedDataPoints);
        writeToCSV(extractedDataPoints);

        p.run().waitUntilFinish();
    }

    private static void writeToCSV(final PCollection<PriceQuery> extractedDataPoints) {
        extractedDataPoints.apply(FileIO.<String, PriceQuery>writeDynamic()
                .via(Contextful.fn((PriceQuery pq) -> Arrays.asList(pq.startDate() + "",
                                pq.queriedAt() + "",
                                pq.price() + "")),
                        Contextful.fn(
                                (String connection) -> new CSVSink(Arrays.asList("startDate", "queriedAt", "price"))))
                .by(input -> input.startStation() + "-" + input.targetStation())
                .to("/tmp/fahrpreisakku/")
                .withDestinationCoder(StringUtf8Coder.of())
                .withNaming(type -> defaultNaming(type, ".csv"))
                .withCompression(Compression.GZIP)
        );
    }

    private static void writeToDB(final PCollection<PriceQuery> extractedDataPoints) {
        extractedDataPoints.apply(JdbcIO.<PriceQuery>write()
                .withDataSourceConfiguration(JdbcIO.DataSourceConfiguration.create(
                        "org.mariadb.jdbc.Driver", "jdbc:mariadb://localhost:3306/fahrpreise")
                )
                .withStatement("INSERT INTO fahrpreise.preis_query (`from`,`to`,queried_at,price,start_date)" +
                        "VALUES (?,?,?,?,?)")
                .withPreparedStatementSetter((JdbcIO.PreparedStatementSetter<PriceQuery>) (element, query) -> {
                    query.setLong(1, element.startStation());
                    query.setLong(2, element.targetStation());
                    query.setLong(3, element.queriedAt());
                    query.setDouble(4, element.price());
                    query.setLong(5, element.startDate());
                })
        );
    }

    private static void setupTools() {
        BrotliLoader.isBrotliAvailable();
        Configuration.setDefaults(new Configuration.Defaults() {

            private final JsonProvider jsonProvider = new JacksonJsonProvider();
            private final MappingProvider mappingProvider = new JacksonMappingProvider();

            @Override
            public JsonProvider jsonProvider() {
                return jsonProvider;
            }

            @Override
            public MappingProvider mappingProvider() {
                return mappingProvider;
            }

            @Override
            public Set<Option> options() {
                return EnumSet.noneOf(Option.class);
            }
        });
    }

    private static Iterable<PriceQuery> getPriceQueries(FileIO.ReadableFile f) {
        Object document = null;
        try {
            BrotliInputStream brotliInputStream = new BrotliInputStream(new ByteArrayInputStream(f.readFullyAsBytes()));

            document = Configuration.defaultConfiguration().jsonProvider().parse(brotliInputStream, "UTF-8");

            final String[] filename_params = f.getMetadata()
                    .resourceId()
                    .getFilename()
                    .substring(0, "2168494927864-8000706-8000091".length())
                    .split("-");
            long startStation = Long.parseLong(filename_params[1]);
            long targetStation = Long.parseLong(filename_params[2]);

            List<PriceQuery> results = new ArrayList<>();
            List<Number> prices = PRICE_PATH.read(document);
            // those differ from the one in the filename. why?
            //List<String> startStations = JsonPath.read(document, "$.data.*.*.legs[0].origin.id");
            //List<String> endStations = JsonPath.read(document, "$.data.*.*.legs[-1].origin.id");
            List<String> startTimes = START_TIME_PATH.read(document);
            List<String> endTimes = END_TIME_PATH.read(document);
            final int size = prices.size();
            if (startTimes.size() != size || endTimes.size() != size) {
                throw new Exception("sizes of entries from json are not equal");
            }
            final Instant queriedAt = Instant.from(dateTimeFormatter.parse(JsonPath.read(document, "$" +
                    ".queried_at")));
            for (int i = 0; i < size; i++) {
                try {
                    PriceQuery pq = new PriceQuery(
                            queriedAt.toEpochMilli(),
                            prices.get(i).doubleValue(),
                            startStation, targetStation,
                            java.time.Instant.from(dateTimeFormatter.parse(startTimes.get(i))).toEpochMilli(),
                            java.time.Instant.from(dateTimeFormatter.parse(endTimes.get(i))).toEpochMilli()
                    );
                    results.add(pq);
                } catch (Exception e) {
                    log.warn("error during processing {} in document ({},{},{},{})", i, prices.get(i),
                            startTimes.get(i), endTimes.get(i), e);
                }
            }
            return results;
        } catch (Exception e) {
            log.error("could not read file {}: {}", f.getMetadata().resourceId().getFilename(), e.getMessage());
            return new ArrayList<>();
        }
    }
}