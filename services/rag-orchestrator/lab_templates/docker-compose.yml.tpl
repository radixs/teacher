version: "3.9"

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:9.1.4
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
    ports:
      - "${http_port}:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data

  kibana:
    image: docker.elastic.co/kibana/kibana:9.1.4
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "${kibana_port}:5601"
    depends_on:
      - elasticsearch

volumes:
  es_data:
