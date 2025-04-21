import pandas as pd
from pyspark.sql.window import Window
from pyspark.sql import functions as F

import plotly.io as pio
import plotly.express as px
import plotly.graph_objects as go

from wordcloud import WordCloud
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import base64
from io import BytesIO


def pie_newsSources(value_counts_df):

    # extract labels and values
    labels = value_counts_df['source'].tolist()
    values = value_counts_df['count'].tolist()

    # create pie chart
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hoverinfo='label+value+percent',
        hovertemplate="<b>%{label}</b><br>Notícias: %{value}<br>Percentagem: %{percent:.2%}<extra></extra>"
    )])

    fig.update_traces(
        textposition='inside',
        textinfo='label',
        textfont_size=12
    )

    fig.update_layout(
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=25, b=25, l=0, r=0)
    )

    return pio.to_html(fig, full_html=False, config={'displayModeBar': False})


def timeseries_news(df_with_query, news_by_month, query):
    traducao_meses = {
        "January": "janeiro", "February": "fevereiro", "March": "março",
        "April": "abril", "May": "maio", "June": "junho",
        "July": "julho", "August": "agosto", "September": "setembro",
        "October": "outubro", "November": "novembro", "December": "dezembro"
    }

    # get the top 5 keywords for each month
    keywords_by_month = (
        df_with_query
        .select('*', F.explode('keywords'))
        .groupBy("timestamp", "key")
        .agg(F.sum("value").alias("key_mentions"))
        .filter(F.col("key") != query)
        .withColumn("rank", F.row_number().over(Window.partitionBy("timestamp").orderBy(F.desc("key_mentions"))))
        .filter(F.col("rank") <= 5)
        .groupBy("timestamp")
        .agg(F.collect_list("key").alias("top5_keywords"))
        .toPandas()
    )

    # get the count of news for each month
    news_history = news_by_month.merge(keywords_by_month, on="timestamp", how="inner")
    news_history["timestamp"] = pd.to_datetime(news_history["timestamp"].astype(str), format='%Y%m')

    # fill in missing months with 0
    min_date = news_history["timestamp"].min()
    max_date = news_history["timestamp"].max()
    full_range = pd.date_range(start=min_date, end=max_date, freq='MS')

    news_history = news_history.set_index("timestamp").reindex(full_range).fillna(0).reset_index()
    news_history = news_history.rename(columns={"index": "timestamp"})
    news_history = news_history.sort_values(by="timestamp")

    # convert to datetime and format
    news_history["data_formatada"] = news_history["timestamp"].dt.strftime("%B de %Y").replace(traducao_meses, regex=True)
    news_history["top5_keywords"] = news_history["top5_keywords"].map(
        lambda words: "-" if words == 0 else "<br>".join([f"{i+1}. {word}" for i, word in enumerate(words)])
    )

    # create the time series plot
    fig = px.line(
        news_history,
        x="timestamp",
        y="count_of_news",
        line_shape="linear",
        custom_data=news_history[["data_formatada", "top5_keywords"]],
    )

    fig.update_traces(
        hovertemplate="<b>Data:</b> %{customdata[0]}<br>"
                    "<b>Notícias:</b> %{y}<br>"
                    "<b>Relações em Destaque:</b><br>%{customdata[1]}"
    )

    fig.update_layout(
        xaxis_title="Data",
        yaxis_title="Quantidade de Notícias",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=0, b=0, l=0, r=0),
        xaxis=dict(
            showgrid=False,
            zeroline=True,
            zerolinecolor="black",
            linecolor="black",
            linewidth=2
        ),
        yaxis=dict(
            range=[0, max(news_history["count_of_news"])*1.1],
            showgrid=True,  
            gridcolor="lightgray",  
            zeroline=True,
            zerolinecolor="black",
            linecolor="black",
            linewidth=2
        ),
    )

    fig.update_traces(line=dict(color='rgb(101, 110, 242)'),
                    hoverlabel=dict(bgcolor='rgb(101, 110, 242)',
                                    bordercolor='rgb(101, 110, 242)',
                                    font=dict(color='white')))


    fig.update_xaxes(tickformat="%Y-%m")

    return pio.to_html(fig, full_html=False, config={'displayModeBar': False}), news_history.loc[0, "data_formatada"]


def topic_wordcloud(word_counts, TEXT, FONT_PATH,
                    MAX_FONT_SIZE=500,
                    IMAGE_SIZE=(2250, 400)):
    # validate word_counts
    if word_counts == {}:
        word_counts = {"abracadabra": 1}
        wcloud_colour = "rgb(34, 36, 170)"

    else:
        wcloud_colour = "white"

    # get optimal font size and calculate centered position (function)
    def get_optimal_font_size(text, font_path, max_size, image_size):
        for size in range(max_size, 5, -5):
            font = ImageFont.truetype(font_path, size=size)
            temp_img = Image.new("RGBA", image_size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(temp_img)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            bbox2 = draw.textbbox((0, 0), f"lpLGlpPiIX{text}", font=font)
            text_height = bbox2[3] - bbox2[1]

            if text_width <= image_size[0]*0.95 and text_height <= image_size[1]*0.95:  
                return font, text_width, text_height
            
        return font, text_width, text_height

    # get optimal font size and calculate centered position (execution)
    font, text_width, text_height = get_optimal_font_size(TEXT, FONT_PATH, MAX_FONT_SIZE, IMAGE_SIZE)
    x_offset = (IMAGE_SIZE[0] - text_width) // 2
    y_offset = (IMAGE_SIZE[1] - text_height*1.3) // 2

    # create the base canvas and mask
    canvas = Image.new("RGBA", IMAGE_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.text((x_offset, y_offset), TEXT, fill=(34, 36, 170, 255), font=font)
    mask = np.array(canvas.convert("L"))
    draw.text(
        (x_offset, y_offset),
        TEXT,
        fill=(34, 36, 170, 255), # topic letters
        font=font,
        stroke_width=3,
        stroke_fill=(255, 255, 255, 255) # topic contour
    )
    
    # generate wcloud inside the mask # HOW CAN I AMPPLIFY THE WORDS?
    wc = WordCloud(
        mode="RGBA",
        background_color=None,
        mask=~mask,
        min_font_size=1,
        color_func=lambda *args, **kwargs: wcloud_colour,
    ).generate_from_frequencies(word_counts)

    # create output image
    wc_image = wc.to_image()
    final_img = Image.alpha_composite(canvas, wc_image)

    # output the image as base64
    def pil_to_base64(img):
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    base64_img = pil_to_base64(final_img)

    return base64_img


if __name__ == '__main__':
    print("abracadabra")