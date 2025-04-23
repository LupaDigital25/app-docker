# Flask
from flask import Flask, render_template, request

# Spark
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import *

# Others
import os
import re
import unicodedata
import atexit

# Local
from graph import create_keyword_graph
from info import pie_newsSources, timeseries_news, topic_wordcloud
from info2 import ts_topicrelation, sources_topicrelation, news_topicrelation

# Functions
def standardize_keyword(texto):
    texto = texto.lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

# Environment variables
spark_cores = os.getenv("SPARK_CORES", "*")
spark_mem = os.getenv("SPARK_MEM", "8g")

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

# start the spark session
spark = SparkSession.builder \
    .appName("LupaDigital") \
    .master(f"local[{spark_cores}]") \
    .config("spark.ui.enabled", "false") \
    .config("spark.driver.memory", f"{spark_mem}") \
    .config("spark.executor.memory", f"{spark_mem}") \
    .getOrCreate()

# gracefully stop the spark session on exit
atexit.register(lambda: spark.stop())

# read the data
df = spark.read.parquet("../data/news_processed")

# set some default variables
globalVar = {
            "search_done": False,
            "zero_results": True,
            "topicrelation": False,
            "total_amount_of_news": 349519, #df.count()
            "first_news": 1998, #df.select("timestamp").orderBy("timestamp").first()[0])
            "last_news": 2024, #df.select("timestamp").orderBy(df.timestamp.desc()).first()[0]
            "graph_html": (None, None),
            }

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html', globalVar=globalVar)


@app.route('/sobre')
def sobre():
    global globalVar
    if globalVar["search_done"] == False:
        return render_template('404.html', globalVar=globalVar)
    
    return render_template('info.html', globalVar=globalVar)


@app.route('/grafo')
def grafo():
    global globalVar
    if globalVar["search_done"] == False or globalVar["zero_results"] == True:
        return render_template('404.html', globalVar=globalVar)
    
    # if graph was already computed, ok
    if globalVar["graph_html"][0] == globalVar["query"]:
        return render_template('graph.html', globalVar=globalVar)
    
    # if graph has yet to be computed, do it
    if globalVar["graph_html"][0] != globalVar["query"]:
        top_n = (
            globalVar["result"].sortBy(lambda x: x[1][0], ascending=False)
                .take(125)
        )
        min_count = min(x[1][0] for x in top_n)
        globalVar["graph_html"] = (globalVar["query"],
                                   create_keyword_graph(dict(top_n), globalVar["query"], min_count))
        return render_template('graph.html', globalVar=globalVar)


@app.route('/pesquisa', methods=['GET'])
def pesquisa():
    global globalVar

    # update
    globalVar["search_done"] = True
    globalVar["zero_results"] = False
    globalVar["topicrelation"] = False

    # free up memory
    globalVar["graph_html"] = (None, None)
    globalVar["count_topicrelation"] = None
    globalVar["sentiment_topicrelation"] = None
    globalVar["sources_topicrelation"] = None
    globalVar["ts_topicrelation"] = None
    globalVar["news_topicrelation"] = None

    # query requested
    query = request.args.get('topico', '')
    globalVar['query'] = query

    # data filtering
    df_with_query = df \
                    .filter(F.array_contains(df["significant_keywords"], standardize_keyword(query))) \
                    .drop("significant_keywords")
    globalVar['query_amountofnews'] = df_with_query.count()

    # if there are no results show there is nothing
    if globalVar['query_amountofnews'] == 0:
        globalVar["zero_results"] = True
        globalVar["wordcloud"] = topic_wordcloud({}, query, "static/Roboto-Black.ttf")
        globalVar["graph_html"] = (query, None)
        return render_template('info.html', globalVar=globalVar)
    
    # process the query results
    # create key value pairs for each seen keyword
    result = df_with_query.rdd.flatMap(lambda row: [
        (key, (
            value if value is not None else 0,
            {row["timestamp"]: value if value is not None else 0},
            (row["sentiment"] or 0.0) * (value if value is not None else 0),
            {row["source"]: 1},
            [row["archive"]] if row["archive"] is not None else []
        )) for key, value in (row["keywords"] or {}).items()
    ])
    # reduce the key value pairs to a single value
    result = result.reduceByKey(lambda a, b: (
        a[0] + b[0],  # sum counts
        {ts: a[1].get(ts, 0) + b[1].get(ts, 0) for ts in set(a[1]) | set(b[1])},  # merge timestamp dictionaries
        a[2] + b[2],  # sum sentiments
        {source: a[3].get(source, 0) + b[3].get(source, 0) for source in set(a[3]) | set(b[3])},  # merge source dictionaries
        a[4] + b[4]  # concatenate news lists
    ))
    # remove where key is same as standardized keyword
    result = result.filter(lambda x: standardize_keyword(x[0]) != standardize_keyword(query))
    # divide sentiment by count to get average sentiment
    result = result.mapValues(lambda x: (
        x[0],
        x[1],
        x[2] / x[0] if x[0] > 0 else 0,
        x[3],
        x[4]
    ))
    globalVar["result"] = result
    del result

    # get insights and visualizations
    # info: wordcloud
    word_counts = word_counts = dict(
        globalVar["result"].map(lambda x: (x[0], x[1][0])).take(5000)
    )
    globalVar["wordcloud"] = topic_wordcloud(word_counts, query, "static/Roboto-Black.ttf")
    del word_counts
    # info: sources pie
    globalVar["pie_sources"] = pie_newsSources(df_with_query.groupBy('source').count().toPandas()) 
    # info: time series
    globalVar["news_by_month"] = (
        df_with_query
        .groupBy('timestamp')
        .agg(F.count('archive').alias('count_of_news'))
        .toPandas()
    )
    globalVar["ts_news"], globalVar["query_firstnews"] = timeseries_news(df_with_query, globalVar["news_by_month"], query)
    # info: topic relation deactivated
    globalVar["topicrelation"] = False

    # render the info template
    return render_template('info.html', globalVar=globalVar)


@app.route('/relacao', methods=['GET'])
def relacao():
    global globalVar
    if globalVar["search_done"] == False or globalVar["zero_results"] == True:
        return render_template('404.html', globalVar=globalVar)
    
    # topic relation requested
    related_topic = request.args.get('entre', '')
    globalVar['related_topic'] = related_topic
    standardize_related_topic = standardize_keyword(related_topic)

    # get the topic relation
    try:
        filtered = dict(globalVar["result"].filter(lambda x: standardize_keyword(x[0]) == standardize_related_topic).collect())
        filtered =  next(iter(filtered.values()))
        globalVar["topicrelation_exists"] = True
    except:
        globalVar["topicrelation_exists"] = False


    # either return results
    if globalVar["topicrelation_exists"]:
        # relation count
        globalVar["count_topicrelation"] = filtered[0]
        # relation sentiment
        globalVar["sentiment_topicrelation"] = filtered[2]
        # relation sources
        globalVar["sources_topicrelation"] = sources_topicrelation(filtered[3])
        # relation time series
        globalVar["ts_topicrelation"] = ts_topicrelation(globalVar["news_by_month"], filtered[1], related_topic, globalVar['query'])
        # relation news
        globalVar["news_topicrelation"] = news_topicrelation(filtered[4])
        
    # or return a random selection of topics
    else:
        filtered_sample = (
            globalVar["result"].filter(lambda x: x[1][0] >= 3)
                .takeSample(False, 5)
        )
        recomendation_output = ""
        for x in filtered_sample:
            recomendation_output += f"<a href='/relacao?entre={x[0]}'>{x[0]}</a>, "
        globalVar["recomendations_topicrelation"] = recomendation_output[:-2]

    globalVar["topicrelation"] = True
    return render_template('info.html', globalVar=globalVar, scroll_to_relation=True)
    


if __name__ == '__main__':
    #app.run(debug=True)
    app.run(host="0.0.0.0", port=5000, debug=False)
