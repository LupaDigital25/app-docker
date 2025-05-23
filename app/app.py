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
import pickle
import traceback
import sys

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

def save_to_pickle(session_id, filename, data):
    file_path = os.path.join(f"/tmp/lupa_result_{session_id}", f"{filename}.pickle")
    with open(file_path, "wb") as f:
        pickle.dump(data, f)
    return file_path

def load_from_pickle(file_path):
    try:
        with open(file_path, "rb") as f:
            return pickle.load(f)
    except:
        return None

def merge_dicts(d1, d2):
    for k, v in d2.items():
        d1[k] = d1.get(k, 0) + v
    return d1

def get_spark_session():
    global spark
    try:
        # is JVM alive?
        _ = spark.sparkContext.version  
        return spark
    except Exception:
        try:
            spark.stop()
        except:
            # ignore any errors
            pass
        # force a new session
        spark = None
    # create a new session if the previous one is not alive
    try:
        spark = SparkSession.builder \
            .appName("LupaDigital") \
            .master(f"local[{spark_cores}]") \
            .config("spark.ui.enabled", "false") \
            .config("spark.driver.memory", f"{spark_mem}") \
            .config("spark.executor.memory", f"{spark_mem}") \
            .getOrCreate()
        return spark
    # if there is an error, print the traceback and raise the exception
    except Exception:
        traceback.print_exc()
        raise

# Environment variables
spark_cores = os.getenv("SPARK_CORES", "*")
spark_mem = os.getenv("SPARK_MEM", "6g")

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
df = spark.read.parquet("../data/news_processed").cache()

# sessions cached results
cached_sessions = TTLCache(maxsize=50, ttl=3600)
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
    global cached_sessions

    if "session_id" not in session or session.get("session_id", "") not in cached_sessions:
        session["session_id"] = str(uuid.uuid4())

        # create a new session
        cached_sessions[session["session_id"]] = {}
        output_dir = f"/tmp/lupa_result_{session['session_id']}"
        os.makedirs(output_dir, exist_ok=True)
    
        # set some default variables
        session["search_done"] = False
        session["zero_results"] = True
        session["topicrelation"] = False
        session["total_amount_of_news"] = 349519 #df.count()
        session["first_news"] = 1998 #df.select("timestamp").orderBy("timestamp").first()[0]
        session["last_news"] = 2024 #df.select("timestamp").orderBy(df.timestamp.desc()).first()[0]
        cached_sessions[session["session_id"]]["graph_html"] = save_to_pickle(session["session_id"],
                                                                             "graph_html",
                                                                             [None, None])

@app.route('/health')
def health():
    """healthcheck for docker"""
    global spark
    try:
         _ = spark.sparkContext.version
         return "OK", 200
    except:
        try:
            spark = get_spark_session()
            _ = spark.sparkContext.version
            return "OK", 200
        except Exception as e:
            print("Spark JVM dead. Leaving container.")
            sys.exit(1) # force container to die

@app.route('/')
def home():
    return render_template('index.html', session=session,
                           graph_html_0 = load_from_pickle(cached_sessions[session["session_id"]]["graph_html"])[0])

@app.route('/sobre')
def sobre():
    global cached_sessions

    if not session.get("search_done", False):
        return render_template("404.html", session=session)
    
    return render_template("info.html", session=session,
                           wordcloud = load_from_pickle(cached_sessions[session["session_id"]].get("wordcloud", "")),
                           pie_sources = load_from_pickle(cached_sessions[session["session_id"]].get("pie_sources", "")),
                           ts_news = load_from_pickle(cached_sessions[session["session_id"]].get("ts_news", "")),
                           count_topicrelation = load_from_pickle(cached_sessions[session["session_id"]].get("count_topicrelation", "")),
                           sentiment_topicrelation = load_from_pickle(cached_sessions[session["session_id"]].get("sentiment_topicrelation", "")),
                           sources_topicrelation = load_from_pickle(cached_sessions[session["session_id"]].get("sources_topicrelation", "")),
                           ts_topicrelation = load_from_pickle(cached_sessions[session["session_id"]].get("ts_topicrelation", "")),
                           news_topicrelation = load_from_pickle(cached_sessions[session["session_id"]].get("news_topicrelation", "")),
                           recomendations_topicrelation = load_from_pickle(cached_sessions[session["session_id"]].get("recomendations_topicrelation", "")),
                           graph_html_0 = load_from_pickle(cached_sessions[session["session_id"]]["graph_html"])[0])

@app.route('/grafo')
def grafo():
    global cached_sessions
    spark = get_spark_session()

    if not session.get("search_done", False) or session.get("zero_results", True):
        return render_template('404.html', session=session)
    
    graph_html = load_from_pickle(cached_sessions[session["session_id"]]["graph_html"])
    
    # if graph was already computed, ok
    if graph_html[0] == session["query"]:
        return render_template('graph.html', session=session,
                               graph_html=graph_html[1])
    
    # if graph has yet to be computed, do it
    if graph_html[0] != session["query"]:
        result_path = cached_sessions[session["session_id"]]["result"]
        result = spark.sparkContext.pickleFile(result_path)
        top_n = result.top(125, key=lambda x: x[1][0])
        min_count = top_n[-1][1][0]
        graph_html = [session["query"], create_keyword_graph(dict(top_n), session["query"], min_count)]
        cached_sessions[session["session_id"]]["graph_html"] = save_to_pickle(session["session_id"],
                                                                              "graph_html", graph_html)
        return render_template('graph.html', session=session,
                               graph_html=graph_html[1])    


@app.route('/pesquisa', methods=['GET'])
def pesquisa():
    global cached_sessions
    spark = get_spark_session()

    # update
    session["search_done"] = True
    session["topicrelation"] = False

    # query requested
    query = request.args.get('topico', '')
    
    if session.get("query", "") == query:
        return render_template('info.html', session=session,
                               wordcloud = load_from_pickle(cached_sessions[session["session_id"]].get("wordcloud", "")),
                               pie_sources = load_from_pickle(cached_sessions[session["session_id"]].get("pie_sources", "")),
                               ts_news = load_from_pickle(cached_sessions[session["session_id"]].get("ts_news", "")))
    
    # free up memory
    cleanup_untracked_pickles(cached_sessions)

    session['query'] = query

    # data filtering
    df_with_query = df \
                    .filter(F.array_contains(df["significant_keywords"], standardize_keyword(query))) \
                    .drop("significant_keywords")
    session['query_amountofnews'] = df_with_query.count()

    # if there are no results show there is nothing
    if session['query_amountofnews'] == 0:
        session["zero_results"] = True

        cached_sessions[session["session_id"]]["wordcloud"] = save_to_pickle(session["session_id"],
                                                                             "wordcloud",
                                                                             topic_wordcloud({}, query, "static/Roboto-Black.ttf"))
        cached_sessions[session["session_id"]]["graph_html"] = save_to_pickle(session["session_id"],
                                                                             "graph_html",
                                                                             [query, None])
        return render_template('info.html', session=session,
                               wordcloud = load_from_pickle(cached_sessions[session["session_id"]]["wordcloud"]),
                               graph_html_0 = load_from_pickle(cached_sessions[session["session_id"]]["graph_html"])[0])
    
    session["zero_results"] = False
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
        merge_dicts(a[1], b[1]),  # merge timestamp dictionaries
        a[2] + b[2],  # sum sentiments
        merge_dicts(a[3], b[3]),  # merge source dictionaries
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
    result_path = f"/tmp/lupa_result_{session['session_id']}/result"
    if os.path.exists(result_path):
        shutil.rmtree(result_path)
    result.saveAsPickleFile(result_path)
    cached_sessions[session["session_id"]]["result"] = result_path
    del result
    cached_sessions[session["session_id"]]["wordcloud"] = save_to_pickle(session["session_id"],
                                                                             "wordcloud",
                                                                             topic_wordcloud(word_counts, query, "static/Roboto-Black.ttf"))
    del word_counts
    # info: sources pie
    cached_sessions[session["session_id"]]["pie_sources"] = save_to_pickle(session["session_id"],
                                                                             "pie_sources",
                                                                             pie_newsSources(df_with_query.groupBy('source').count().toPandas()))
    # info: time series
    news_by_month = (
        df_with_query
        .groupBy('timestamp')
        .agg(F.count('archive').alias('count_of_news'))
        .toPandas()
    )
    cached_sessions[session["session_id"]]["news_by_month"] = save_to_pickle(session["session_id"],
                                                                             "news_by_month", news_by_month)
    ts_news, session["query_firstnews"] = timeseries_news(df_with_query, news_by_month, query)
    cached_sessions[session["session_id"]]["ts_news"] = save_to_pickle(session["session_id"],
                                                                             "ts_news", ts_news) 

    # render the info template
    return render_template('info.html', session=session,
                           wordcloud = load_from_pickle(cached_sessions[session["session_id"]]["wordcloud"]),
                           pie_sources = load_from_pickle(cached_sessions[session["session_id"]]["pie_sources"]),
                           ts_news = load_from_pickle(cached_sessions[session["session_id"]]["ts_news"]))



@app.route('/relacao', methods=['GET'])
def relacao():
    spark = get_spark_session()

    if not session.get("search_done", False) or session.get("zero_results", True):
        return render_template('404.html', session=session)
    
    # topic relation requested
    related_topic = request.args.get('entre', '')
    session['related_topic'] = related_topic
    standardize_related_topic = standardize_keyword(related_topic)

    # get the topic relation
    result_path = cached_sessions[session["session_id"]]["result"]
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
        cached_sessions[session["session_id"]]["count_topicrelation"] = save_to_pickle(session["session_id"],
                                                                                     "count_topicrelation", filtered[0])
        # relation sentiment
        cached_sessions[session["session_id"]]["sentiment_topicrelation"] = save_to_pickle(session["session_id"],
                                                                                           "sentiment_topicrelation", filtered[2])
        # relation sources
        cached_sessions[session["session_id"]]["sources_topicrelation"] = save_to_pickle(session["session_id"],
                                                                                         "sources_topicrelation",
                                                                                         sources_topicrelation(filtered[3]))
        # relation time series
        ts_topicrelation_var = ts_topicrelation(load_from_pickle(cached_sessions[session["session_id"]]["news_by_month"]),
                                                       filtered[1],
                                                       related_topic,
                                                       session['query'])
        cached_sessions[session["session_id"]]["ts_topicrelation"] = save_to_pickle(session["session_id"],
                                                                                     "ts_topicrelation", ts_topicrelation_var)
        # relation news
        cached_sessions[session["session_id"]]["news_topicrelation"] = save_to_pickle(session["session_id"],
                                                                                      "news_topicrelation",
                                                                                      news_topicrelation(filtered[4]))
        
        cached_sessions[session["session_id"]]["recomendations_topicrelation"] = save_to_pickle(session["session_id"],
                                                                                                "recomendations_topicrelation",
                                                                                                "")
        
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
        cached_sessions[session["session_id"]]["recomendations_topicrelation"] = save_to_pickle(session["session_id"],
                                                                                                "recomendations_topicrelation",
                                                                                                recomendation_output[:-2])
        
        cached_sessions[session["session_id"]]["count_topicrelation"] = save_to_pickle(session["session_id"],
                                                                                     "count_topicrelation", "")
        cached_sessions[session["session_id"]]["sentiment_topicrelation"] = save_to_pickle(session["session_id"],
                                                                                           "sentiment_topicrelation", "")
        cached_sessions[session["session_id"]]["sources_topicrelation"] = save_to_pickle(session["session_id"],
                                                                                         "sources_topicrelation",
                                                                                         "")
        cached_sessions[session["session_id"]]["ts_topicrelation"] = save_to_pickle(session["session_id"],
                                                                                     "ts_topicrelation", "")
        cached_sessions[session["session_id"]]["news_topicrelation"] = save_to_pickle(session["session_id"],
                                                                                      "news_topicrelation",
                                                                                      "")
        

    session["topicrelation"] = True
    return render_template('info.html', session=session, scroll_to_relation=True,
                           wordcloud = load_from_pickle(cached_sessions[session["session_id"]]["wordcloud"]),
                           pie_sources = load_from_pickle(cached_sessions[session["session_id"]]["pie_sources"]),
                           ts_news = load_from_pickle(cached_sessions[session["session_id"]]["ts_news"]),
                           count_topicrelation = load_from_pickle(cached_sessions[session["session_id"]]["count_topicrelation"]),
                           sentiment_topicrelation = load_from_pickle(cached_sessions[session["session_id"]]["sentiment_topicrelation"]),
                           sources_topicrelation = load_from_pickle(cached_sessions[session["session_id"]]["sources_topicrelation"]),
                           ts_topicrelation = load_from_pickle(cached_sessions[session["session_id"]]["ts_topicrelation"]),
                           news_topicrelation = load_from_pickle(cached_sessions[session["session_id"]]["news_topicrelation"]),
                           recomendations_topicrelation = load_from_pickle(cached_sessions[session["session_id"]]["recomendations_topicrelation"]),
                           graph_html_0 = load_from_pickle(cached_sessions[session["session_id"]]["graph_html"])[0])


if __name__ == '__main__' and True == True:
    #app.run(debug=True)
    app.run(host="0.0.0.0", port=5000, debug=False)
