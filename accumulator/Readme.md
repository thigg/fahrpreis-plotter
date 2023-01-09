
# Fahrpreis accumulator

transforms the brotli files that the service produces into accumulated summary

This is an apache beam pipeline that reads the brotli files, decompresses them and transfroms them into the single data points

## todo:
 - sort the datapoints in the order they are going to be plotted
 - make faster
 - 


## db schema
 a bit slow

```sql
create table preis_query
(
    id         int auto_increment
        primary key,
    `from`     int         null,
    `to`       int         null,
    queried_at varchar(24) null,
    price      float       null,
    start_date varchar(24) null
);

create index preis_query_from_to_index
    on preis_query (`from`, `to`);
```


## timings
java pipelines+jackson+bz2: 345380ms
java pipelines+jackson+gz: 270938ms
ram+brotli4j: 438696ms
