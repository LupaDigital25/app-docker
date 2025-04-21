import matplotlib
matplotlib.use('Agg')

import networkx as nx
import plotly.graph_objects as go
import numpy as np
import matplotlib.pyplot as plt
import base64
from io import BytesIO

def rgb_string_to_hex(rgb_string):
    rgb_values = rgb_string.strip('rgb()').split(',')
    rgb = tuple(int(value.strip()) for value in rgb_values)
    return '#{:02X}{:02X}{:02X}'.format(rgb[0], rgb[1], rgb[2])


# === CODE ===
class Node:
    def __init__(self, name, node_data, globalVar):
        self.name = name
        self.count = node_data[0]
        self.timestamps = node_data[1]
        self.sentiment = node_data[2]
        self.sources = node_data[3]
        self.news = sorted(node_data[4], reverse=True)
        
        # auxiliary variables
        self.query = globalVar["query"]
        self.min_count = globalVar["min_count"]
        self.sentiment_class = self._sentiment_class()
        self.news_first, self.news_last = self._news_dates()
        self.news_urls = self._news_websites()
        self.news_plot = self._news_plot()
        self.news_sources = self._news_sources()

    def _sentiment_class(self):
        if self.sentiment <= -0.75:
            return "muito negativo"
        elif self.sentiment <= -0.25:
            return "negativo"
        elif self.sentiment < 0.25:
            return "neutro"
        elif self.sentiment < 0.75:
            return "positivo"
        else:
            return "muito positivo"

    def _news_dates(self):
        first_website = self.news[-1].split("/")
        first_website_date = first_website[5][:4] + "/" + first_website[5][4:6]
        last_website = self.news[0].split("/")
        last_website_date = last_website[5][:4] + "/" + last_website[5][4:6]
        return first_website_date, last_website_date
    
    def _news_websites(self):
        websites_data = ""
        for url in self.news[:2500]: # query=Portugal: (100, 52s) (500, 52s) (2500, 57s)
            website = url.split("/")
            websites_data += f"<p><a href='{url}' target='_blank'>{website[5][:4]+'/'+website[5][4:6]+' - '+ '/'.join(website[6:])}</a></p>"
        return websites_data
    
    def _news_plot(self):
        times_said_by_year = {str(k): 0 for k in range(int(self.news_first[:4]),
                                                int(self.news_last[:4])+1)}
        for key in self.timestamps.keys():
            times_said_by_year[str(key)[:4]] += int(self.timestamps[key])
        plt.figure(figsize=(6, 4))
        plt.bar(times_said_by_year.keys(), times_said_by_year.values(), color=rgb_string_to_hex(self.node_color()))
        plt.xlabel('Ano')
        plt.ylabel('Número de Menções')
        plt.xticks(rotation=45)
        plt.grid(axis='y', alpha=0.2)
        plt.tight_layout()
        buffer = BytesIO()
        plt.savefig(buffer, format='png', transparent=True)
        plt.close() 
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')
    
    def _news_sources(self):
        source_data = ""
        for key in self.sources.keys():
            if self.sources[key] is not None:
                source_data += f"<li>{key}: {int(self.sources[key])}</li>"
        return source_data

    def node_text(self):
        if " " in self.name:
            splitted_text = self.name.split(" ")
            mid_text = len(splitted_text)//2
            return ' '.join(splitted_text[:mid_text]) + '<br>' + ' '.join(splitted_text[mid_text:])
        else:
            return self.name
        
    def node_form(self):
        return "circle"
    
    def node_color(self):
        mapping = {
            "muito negativo": "rgb(204, 0, 0)",
            "negativo": "rgb(239, 83, 80)",
            "neutro": "rgb(204, 204, 204)",
            "positivo": "rgb(102, 187, 106)",
            "muito positivo": "rgb(0, 200, 81)"
        }
        return mapping[self.sentiment_class]
    
    def node_size(self):
        return ((np.log(self.count/self.min_count))*3)**1.5 + 50
        
    def node_hovertext(self):
        return (
            f"""Tópico: {self.name}
            <br>Menções: {int(self.count)}
            <br>Último registo: {self.news_last}"""
        )

    def node_customdata(self):
        return (
            f"""
            <h2 style="text-align: center;">Associação entre<br>{self.query} e {self.name}</h2>
            <p>Menções: {int(self.count)}</p>
            <p>Sentimento: {self.sentiment_class}</p>
            <p>Fontes:</p>
            <ul>
            {self.news_sources}
            </ul>
            <div class="url-navigation">
                <button onclick="navigateUrl(-1)">&lt;</button>
                <span id="current-url"></span>
                <button onclick="navigateUrl(1)">&gt;</button>
            </div>
            <div id="website-urls">
                {self.news_urls}
            </div>
            <img src="data:image/png;base64,{self.news_plot}" alt="Bar Plot" style="width:100%; height:auto;">
            """
        )


def get_node_positions(data):
    # create the graph
    G = nx.Graph()

    # initialize nodes positions and add center node
    pos = {}
    G.add_node("center")
    pos["center"] = (0, 0)

    # set the spread for node positions
    spread_x = 300
    spread_y = 150
    min_distance = 50

    # add nodes to the graph with attributes and positions
    for word in data.keys():
        G.add_node(word)

        while True:
            x = np.random.uniform(-spread_x, spread_x)
            y = np.random.uniform(-spread_y, spread_y)

            distance_from_center = np.linalg.norm([x, y])

            if distance_from_center >= min_distance:
                pos[word] = (x, y)
                break

    # avoid collisions between nodes
    pos = nx.spring_layout(G, pos=pos, fixed=["center"], k=0.1, iterations=150, scale=1000, seed=21)

    # remove the center node from the graph
    G.remove_node("center")
    del pos["center"]

    # return the node positions
    return pos


def create_graph(node_x, node_y,
                 node_text, node_hovertext,
                 node_color, node_form,
                 node_size, custom_data):
    # create the figure
    fig = go.Figure()

    # draw the nodes
    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=node_text,
            hovertext=node_hovertext,
            marker=dict(
                color=node_color,
                symbol=node_form,
                size=node_size,
                line=dict(color="black", width=1)
            ),
            hoverinfo="text",
            customdata=custom_data,
            hoverlabel=dict(
                font=dict(color="rgb(48, 62, 92)"),
                bordercolor="rgb(48, 62, 92)"
            )
        )
    )

    # update the fig layout
    fig.update_layout(
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="rgb(217, 238, 252)",
        paper_bgcolor="rgb(217, 238, 252)",
    )

    # generate the base html
    html_code = fig.to_html(include_plotlyjs='inline',
                            full_html=True,
                            config={
                                'displaylogo': False,
                                'modeBarButtonsToRemove': [
                                    'select2d',
                                    'lasso2d',
                                    'resetScale2d',
                                    'toImage',
                                ]
                            })

    return html_code


# === CSS/JS for info panel ===
additional_html = """
<style>
    body, html {
        height: 100vh !important;
        width: 100vw !important;
        margin: 0;
        padding: 0;
        font-family: Arial, sans-serif;
    }
    .plotly-graph-div{
        height:100vh !important;
        width:100vw !important;
    }
    #info-panel {
        position: absolute;
        overflow-y: auto;
        right: 0; /* Default to right */
        top: 0;
        width: 300px; /* Fixed width of the panel */
        height: 100%; /* Full height of container */
        background-color: rgb(217, 238, 252);
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.2);
        transform: scale(0); /* Hide initially */
        transition: transform 0.3s ease; /* Smooth slide in */
        z-index: 2; /* Panel above the graph */
        display: flex;
        flex-direction: column; /* Arrange children vertically */
        color: rgb(48, 62, 92);
    }
    #info-panel.open {
        transform: scale(1); /* Slide in the panel */
    }
    .close-button {
        background-color: #ff4c4c;
        color: white;
        border: none;
        padding: 10px;
        cursor: pointer;
        float: right;
        margin-bottom: -15px;
    }
    .close-button:hover {
        background-color: #e04343;
    }
    #website-urls {
        flex: 1; /* Take remaining vertical space */
        max-height: auto; /* Adjust height as needed */
        overflow-x: auto;
        padding: 4px; /* Padding for inner content */
        background-color: #ffffff; /* Background color */
        border: 1px solid #ddd; /* Border for the scrollable area */
        box-shadow: inset 0 0 5px rgba(0,0,0,0.1); /* Inner shadow */
        margin-top: 7px; /* Spacing from the title */
    }
    #website-urls p {
        white-space: nowrap; /* Prevents line breaks within the item */
    }
    p {
        margin: 5px 5px;
    }
    ul {
        margin-top: 0; /* Set the top margin of the unordered list to 0 */
    }
    li {
        margin-bottom: 5px;
    }
    .url-navigation button {
        border: none;
        border-radius: 2px;
        cursor: pointer;
        background-color: #6c757d;
        color: white;
        transition: background-color 0.3s;
    }
    .url-navigation button:hover {
        background-color: #5a6268;
    }
</style>

<div id="info-panel">
    <button class="close-button" onclick="closePanel()">Fechar</button>
    <p id="node-info">Escolha um nó para ver detalhes.</p>
</div>

<script>
    let currentUrlIndex = 0; // Global variable to track the currently displayed URL

    // Function to close the info panel
    function closePanel() {
        var panel = document.getElementById('info-panel');
        if (panel.classList.contains('open')) {
            panel.style.transform = 'scale(0)';
            setTimeout(() => {
                panel.classList.remove('open'); 
            }, 300); 
        }
    }

    function navigateUrl(direction) {
        const urls = document.querySelectorAll("#website-urls p");
        if (urls.length === 0) return;

        // Hide the currently visible URL
        urls[currentUrlIndex].style.display = "none";

        // Update the index based on the direction
        currentUrlIndex += direction;

        // Wrap around if out of bounds
        if (currentUrlIndex < 0) {
            currentUrlIndex = urls.length - 1; // Go to the last URL if moving left
        } else if (currentUrlIndex >= urls.length) {
            currentUrlIndex = 0; // Go back to the first URL if moving right
        }

        // Show the new URL
        urls[currentUrlIndex].style.display = "block";

        // Update the display span with the current index
        document.getElementById("current-url").textContent = `Notícia ${currentUrlIndex + 1}/${urls.length}`;
    }

    // Function to initialize the URL display for a new node
    function initializeUrls() {
        const urls = document.querySelectorAll("#website-urls p");
        urls.forEach((url) => {
            url.style.display = "none"; // Hide all URLs initially
        });

        // Reset index and show the first URL if available
        currentUrlIndex = 0; 
        if (urls.length > 0) {
            urls[currentUrlIndex].style.display = "block"; // Show the first URL
        }
        
        // Update the display span with the initial index
        document.getElementById("current-url").textContent = `Notícia ${currentUrlIndex + 1}/${urls.length}`;
    }

    document.addEventListener('DOMContentLoaded', function() {
        var plotDiv = document.querySelector('.plotly-graph-div');
        
        if (plotDiv) {
            plotDiv.on('plotly_click', function(data) {
                if (data.points.length > 0) {
                    var point = data.points[0];
                    var customData = point.customdata;
                    var nodeX = point.x;
                    var nodeY = point.y

                    if (nodeX === 0 && nodeY === 0) {
                        return;
                    }

                    document.getElementById('node-info').innerHTML = customData; // Use custom data for the panel

                    // Reset the URL index when a new node is clicked
                    currentUrlIndex = 0; // Reset to first URL
                    try {
                        initializeUrls(); // Reinitialize the URLs
                    } catch (error) {
                        // Code to handle the error
                        console.error("An error occurred:", error);
                    }

                    // Determine mouse click position for panel placement
                    var mouseX = data.event.clientX; 
                    var panel = document.getElementById('info-panel');

                    // Adjust panel position based on mouse click
                    if (mouseX > window.innerWidth / 2) {
                        panel.style.left = '0'; 
                        panel.style.right = 'auto'; 
                    } else {
                        panel.style.right = '0'; 
                        panel.style.left = 'auto'; 
                    }

                    panel.classList.add('open'); 
                    panel.style.transform = 'translateX(0)'; // Animate to the open position
                }
            });
        } else {
            console.error("Graph div not found.");
        }
    });
</script>
"""


## === MAIN FUNCTION ===
def create_keyword_graph(data, query, min_count):
    globalVar = {"query": query,
                 "min_count": min_count}

    # lists for node info
    node_x, node_y = [0], [0]
    node_text, node_form = [f"<b>{query}</b>"], ["square"]
    node_size, node_color= [0], ["rgb(217, 238, 252)"]
    node_hovertext, custom_data = ["Explore os tópicos ao clicar neles."], [""]
    
    # sentiment filtering deleted
    pos = get_node_positions(data)

    for key in data.keys():
        node = Node(key, data[key], globalVar)
        node_x.append(pos[key][0])
        node_y.append(pos[key][1])
        node_text.append(node.node_text())
        node_form.append(node.node_form())
        node_size.append(node.node_size())
        node_color.append(node.node_color())
        node_hovertext.append(node.node_hovertext())
        custom_data.append(node.node_customdata())

    # create the graph
    html_code = create_graph(node_x, node_y,
                             node_text, node_hovertext,
                             node_color, node_form,
                             node_size, custom_data)

    #with open("graph_galptest.html", 'w') as f:
    #    f.write(final_html)

    return html_code.replace("</body>", additional_html + "</body>")


# === TESTING ===
if __name__ == "__main__":
    print("abracadabra")