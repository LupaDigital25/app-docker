# Flask
from flask import Flask, render_template, request, session

# Spark
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import *

# Others
import os
import re
import unicodedata
import atexit
import uuid
import shutil
from cachetools import TTLCache

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

# results for query searches by session_id (cache)
results = TTLCache(maxsize=50, ttl=300)
def cleanup_untracked_pickles(cache):
    """Delete all pickle folders not currently in cache."""
    try:
        active_sessions = set(str(sid) for sid in cache.keys())
        for entry in os.listdir("/tmp"):
            full_path = os.path.join("/tmp", entry)
            if entry.startswith("lupa_result_"):
                session_id = entry.replace("lupa_result_", "")
                if session_id not in active_sessions:
                    print(f"Deleting old cache: {full_path}")
                    shutil.rmtree(full_path, ignore_errors=True)
    except Exception as e:
        print(f"Cleanup failed: {e}")

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

app = Flask(__name__)
app.secret_key = "abracadabra2"

@app.before_request
def setup_user():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    
        # set some default variables
        session["search_done"] = False
        session["zero_results"] = True
        session["topicrelation"] = False
        session["total_amount_of_news"] = 349519 #df.count()
        session["first_news"] = 1998 #df.select("timestamp").orderBy("timestamp").first()[0]
        session["last_news"] = 2024 #df.select("timestamp").orderBy(df.timestamp.desc()).first()[0]
        session["graph_html"] = [None, None]

@app.route('/')
def home():
    return render_template('index.html', session=session)

@app.route('/sobre')
def sobre():
    if not session.get("search_done", False):
        return render_template("404.html", session=session)
    
    return render_template("info.html", session=session)


@app.route('/grafo')
def grafo():
    global results

    if not session.get("search_done", False) or session.get("zero_results", True):
        return render_template('404.html', session=session)
    
    # if graph was already computed, ok
    if session["graph_html"][0] == session["query"]:
        return render_template('graph.html', session=session)
    
    # if graph has yet to be computed, do it
    if session["graph_html"][0] != session["query"]:
        result_path = results[session["session_id"]]
        result = spark.sparkContext.pickleFile(result_path)
        top_n = (
            result.sortBy(lambda x: x[1][0], ascending=False)
                .take(125)
        )
        min_count = min(x[1][0] for x in top_n)
        session["graph_html"] = [session["query"],
                                   create_keyword_graph(dict(top_n), session["query"], min_count)]
        return render_template('graph.html', session=session)


@app.route('/pesquisa', methods=['GET'])
def pesquisa():
    global results

    # update
    session["search_done"] = True
    session["zero_results"] = False
    session["topicrelation"] = False

    # free up memory
    cleanup_untracked_pickles(results)
    session["graph_html"] = [None, None]
    session["count_topicrelation"] = None
    session["sentiment_topicrelation"] = None
    session["sources_topicrelation"] = None
    session["ts_topicrelation"] = None
    session["news_topicrelation"] = None

    # query requested
    query = request.args.get('topico', '')
    session['query'] = query

    # data filtering
    df_with_query = df \
                    .filter(F.array_contains(df["significant_keywords"], standardize_keyword(query))) \
                    .drop("significant_keywords")
    session['query_amountofnews'] = df_with_query.count()

    # if there are no results show there is nothing
    if session['query_amountofnews'] == 0:
        session["zero_results"] = True
        session["wordcloud"] = topic_wordcloud({}, query, "static/Roboto-Black.ttf")
        session["graph_html"] = [query, None]
        return render_template('info.html', session=session)
    
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

    # get insights and visualizations
    # info: wordcloud
    word_counts = word_counts = dict(
        result.map(lambda x: (x[0], x[1][0])).take(5000)
    )
    result_path = f"/tmp/lupa_result_{session['session_id']}"
    result.saveAsPickleFile(result_path)
    results[session["session_id"]] = result_path
    del result
    session["wordcloud"] = topic_wordcloud(word_counts, query, "static/Roboto-Black.ttf")
    del word_counts
    # info: sources pie
    session["pie_sources"] = pie_newsSources(df_with_query.groupBy('source').count().toPandas()) 
    # info: time series
    session["news_by_month"] = (
        df_with_query
        .groupBy('timestamp')
        .agg(F.count('archive').alias('count_of_news'))
        .toPandas()
    )
    session["ts_news"], session["query_firstnews"] = timeseries_news(df_with_query, session["news_by_month"], query)
    # info: topic relation deactivated
    session["topicrelation"] = False

    # render the info template
    return render_template('info.html', session=session)


@app.route('/relacao', methods=['GET'])
def relacao():
    global results

    if not session.get("search_done", False) or session.get("zero_results", True):
        return render_template('404.html', session=session)
    
    # topic relation requested
    related_topic = request.args.get('entre', '')
    session['related_topic'] = related_topic
    standardize_related_topic = standardize_keyword(related_topic)

    # get the topic relation
    result_path = results[session["session_id"]]
    result = spark.sparkContext.pickleFile(result_path)
    try:
        filtered = dict(result.filter(lambda x: standardize_keyword(x[0]) == standardize_related_topic).collect())
        filtered =  next(iter(filtered.values()))
        session["topicrelation_exists"] = True
    except:
        session["topicrelation_exists"] = False


    # either return results
    if session["topicrelation_exists"]:
        del result
        # relation count
        session["count_topicrelation"] = filtered[0]
        # relation sentiment
        session["sentiment_topicrelation"] = filtered[2]
        # relation sources
        session["sources_topicrelation"] = sources_topicrelation(filtered[3])
        # relation time series
        session["ts_topicrelation"] = ts_topicrelation(session["news_by_month"], filtered[1], related_topic, session['query'])
        # relation news
        session["news_topicrelation"] = news_topicrelation(filtered[4])
        
    # or return a random selection of topics
    else:
        filtered_sample = (
            result.filter(lambda x: x[1][0] >= 3)
                .takeSample(False, 5)
        )
        del result
        recomendation_output = ""
        for x in filtered_sample:
            recomendation_output += f"<a href='/relacao?entre={x[0]}'>{x[0]}</a>, "
        session["recomendations_topicrelation"] = recomendation_output[:-2]

    session["topicrelation"] = True
    return render_template('info.html', session=session, scroll_to_relation=True)
    

if __name__ == '__main__' and True == False:
    #app.run(debug=True)
    app.run(host="0.0.0.0", port=5000, debug=False)
