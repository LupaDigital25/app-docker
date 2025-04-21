import re
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio


def ts_topicrelation(news_by_month, tstampsdict, search_topic, query):

    # create a copy of the news_by_month dataframe
    news_by_monthc = news_by_month.copy()
    news_by_monthc["timestamp"] = pd.to_datetime(news_by_monthc["timestamp"].astype(str), format='%Y%m')

    # number of mentions of the specific keyword
    specific_keyword = pd.DataFrame(list(tstampsdict.items()), columns=["date", "count_specific_keyword"])
    specific_keyword["date"] = pd.to_datetime(specific_keyword["date"], format="%Y%m")

    # merge the two dataframes
    news_history = news_by_monthc.merge(specific_keyword, left_on="timestamp", right_on="date", how="left")

    # create full data range
    min_date = news_history["timestamp"].min()
    max_date = news_history["timestamp"].max()
    full_range = pd.date_range(start=min_date, end=max_date, freq='MS')
    news_history = news_history.set_index("timestamp").reindex(full_range).fillna(0).reset_index()
    news_history = news_history.rename(columns={"index": "timestamp"})
    news_history = news_history.sort_values(by="timestamp")

    # create the plot
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=news_history["timestamp"],
        y=news_history["count_of_news"],
        mode="lines",
        name=f"Notícias sobre {query}",
        hovertemplate="%{y}"
    ))

    fig.add_trace(go.Scatter(
        x=news_history["timestamp"],
        y=news_history["count_specific_keyword"],
        mode="lines",
        name=f"Menções de {search_topic} em notícias sobre {query}",
        hovertemplate="%{y}"
    ))

    fig.update_layout(
        xaxis_title="Data",
        yaxis_title="Contagem",
        hovermode="x unified",
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
            range=[0, max(news_history["count_of_news"].max(), news_history["count_specific_keyword"].max()) * 1.1],
            showgrid=True,  
            gridcolor="lightgray",  
            zeroline=True,
            zerolinecolor="black",
            linecolor="black",
            linewidth=2
        ),
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor="rgba(255,255,255,1)",
            bordercolor="black",
            borderwidth=1
        ),
    )

    fig.data[0].update(line=dict(color='rgba(101, 110, 242, 0.3)'))
    fig.data[1].update(line=dict(color='rgb(101, 110, 242)'))

    fig.update_xaxes(tickformat="%Y-%m")

    return pio.to_html(fig, full_html=False, config={'displayModeBar': False})


def sources_topicrelation(sources):

    # get the sources and their counts
    labels = list(sources.keys())
    values = list(sources.values())

    # create the pie chart
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
        margin=dict(t=0, b=0, l=0, r=0),
        height=None,
        autosize=True
    )

    return fig.to_html(full_html=True, config={'displayModeBar': False})


def news_topicrelation(listofnews):

    company_logos = [
        'record.png',
        'noticiasaominuto.png',
        'lusa.png',
        'jornaldenegocios.png',
        'tsf.png',
        'sicnoticias.png',
        'expresso.png',
        'publico.png',
        'dn.png',
        'observador.png',
        'sapo.png',
        'iol.png',
        'rtp.png',
        'cnn.png',
        'cmjornal.png',
        'jn.png',
        'nit.png',
        'dinheirovivo.png',
        'aeiou.png',
    ]

    divs = {}
    titles = set()

    # iterate through the list of news (only the first 30)
    for url in listofnews[:30]:
        link_content = url.split("/")

        # set title and verify if it is repeated
        title = link_content[-1] if link_content[-1] != "" else link_content[-2]
        title = title.split("?")[0].split("_")[0]
        title = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', title)
        if "-" in title and title not in titles:
            title = title.lower()
            titles.add(title)
        elif title not in titles:
            title = link_content[-1] if link_content[-1] != "" else link_content[-2]
            titles.add(title)
        else:
            continue

        # set date
        date = link_content[5]
        date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"

        # set source
        company = link_content[8].replace("www.", "")

        # get source logo if exists
        is_there_a_logo = False
        for img in company_logos:
            if img[:-4] in company:
                img = f"static/img/logo_{img}"
                is_there_a_logo = True
                break
        if not is_there_a_logo:
            img = f"static/img/logo_404.png"

        # create the div
        div = f"""
                            <div class="testimonial-item bg-transparent border rounded text-white p-4">
                                <i class="fa fa-quote-left fa-2x mb-3"></i>
                                <a href="{url}" target="_blank" rel="noopener noreferrer" class="d-block text-decoration-none mb-3" style="color: inherit; height: 4.5em;">
                                    <p style="margin: 0; text-overflow: ellipsis; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; height: 100%;">{title}</p>
                                </a>
                                <div class="d-flex align-items-center">
                                    <img class="img-fluid flex-shrink-0 rounded-circle" src="{img}" alt="news source logo" style="width: 50px; height: 50px;">
                                    <div class="ps-3">
                                        <h6 class="text-white mb-1">
                                            {company} 
                                            <a href="{url}" target="_blank" rel="noopener noreferrer" style="margin-left: 5px;">
                                                <i class="bi bi-box-arrow-up-right"></i>
                                            </a>
                                        </h6>
                                        <small>{date[:-3]}</small>
                                    </div>
                                </div>
                            </div>
        """

        # save the div
        if date in divs:
            divs[date].append(div)
        else:
            divs[date] = [div]

    # sort the divs by date and prepare for output
    divs = dict(sorted(divs.items(), key=lambda item: item[0], reverse=True))
    divs = "\n".join([div for divs_list in divs.values() for div in divs_list])

    return divs


if __name__ == "__main__":
    print("abracadabra")