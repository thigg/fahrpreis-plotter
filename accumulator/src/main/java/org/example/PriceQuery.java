package org.example;

import org.apache.beam.sdk.schemas.JavaFieldSchema;
import org.apache.beam.sdk.schemas.annotations.DefaultSchema;

@DefaultSchema(JavaFieldSchema.class)
record PriceQuery(
        long queriedAt,
        double price,
        long startStation,
        long targetStation,
        long startDate,
        long endDate
) {
}
