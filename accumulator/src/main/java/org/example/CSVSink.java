package org.example;

import java.io.IOException;
import java.io.PrintWriter;
import java.nio.channels.Channels;
import java.nio.channels.WritableByteChannel;
import java.util.Collections;
import java.util.List;

import org.apache.beam.sdk.io.FileIO;

class CSVSink implements FileIO.Sink<List<String>> {
   private String header;
   private PrintWriter writer;

   public CSVSink(List<String> colNames) {
     this.header = String.join(",",colNames);
   }

   @Override
   public void open(WritableByteChannel channel) throws IOException {
     writer = new PrintWriter(Channels.newOutputStream(channel));
     writer.println(header);
   }

   @Override
   public void write(List<String> element) throws IOException {
     writer.println(String.join(",",element));
   }

   @Override
   public void flush() throws IOException {
     writer.flush();
   }
 }