import matplotlib.pyplot as plt
import plotly
import plotly.graph_objects as go
import plotly.figure_factory as ff
import seaborn as sns
import pandas as pd
import numpy as np
import re
import os
import sys
from pathlib import Path
from pdb import set_trace
from cvnn.utils import create_folder
import logging
import cvnn

logger = logging.getLogger(cvnn.__name__)

DEFAULT_PLOTLY_COLORS = ['rgb(31, 119, 180)',   # Blue
                         'rgb(255, 127, 14)',   # Orange
                         'rgb(44, 160, 44)',    # Green
                         'rgb(214, 39, 40)',
                         'rgb(148, 103, 189)', 'rgb(140, 86, 75)',
                         'rgb(227, 119, 194)', 'rgb(127, 127, 127)',
                         'rgb(188, 189, 34)', 'rgb(23, 190, 207)']

DEFAULT_MATPLOTLIB_COLORS = plt.rcParams['axes.prop_cycle'].by_key()['color']   # [1:] # Uncomment to remove blue color


def triangulate_histogram(x, y, z):
    # https://community.plot.ly/t/adding-a-shape-to-a-3d-plot/1441/8?u=negu93
    if len(x) != len(y) != len(z):
        raise ValueError("The  lists x, y, z, must have the same length")
    n = len(x)
    if n % 2:
        raise ValueError("The length of lists x, y, z must be an even number")
    pts3d = np.vstack((x, y, z)).T
    pts3dp = np.array([[x[2 * k + 1], y[2 * k + 1], 0] for k in range(1, n // 2 - 1)])
    pts3d = np.vstack((pts3d, pts3dp))
    # triangulate the histogram bars:
    tri = [[0, 1, 2], [0, 2, n]]
    for k, i in zip(list(range(n, n - 3 + n // 2)), list(range(3, n - 4, 2))):
        tri.extend([[k, i, i + 1], [k, i + 1, k + 1]])
    tri.extend([[n - 3 + n // 2, n - 3, n - 2], [n - 3 + n // 2, n - 2, n - 1]])
    return pts3d, np.array(tri)


def add_transparency(color='rgb(31, 119, 180)', alpha=0.5):
    pattern = re.compile("^rgb\([0-9]+, [0-9]+, [0-9]+\)$")
    if not re.match(pattern, color):
        logger.error("Unrecognized color format")
        sys.exit(-1)
    color = re.sub("^rgb", "rgba", color)
    color = re.sub("\)$", ", {})".format(alpha), color)
    return color


def extract_values(color='rgb(31, 119, 180)'):
    pattern = re.compile("^rgb\([0-9]+, [0-9]+, [0-9]+\)$")
    if not re.match(pattern, color):
        logger.error("Unrecognized color format")
        sys.exit(-1)
    return [float(s) for s in re.findall(r'\b\d+\b', color)]


def find_intersection_of_gaussians(m1, m2, std1, std2):
    a = 1 / (2 * std1 ** 2) - 1 / (2 * std2 ** 2)
    b = m2 / (std2 ** 2) - m1 / (std1 ** 2)
    c = m1 ** 2 / (2 * std1 ** 2) - m2 ** 2 / (2 * std2 ** 2) - np.log(std2 / std1)
    return np.roots([a, b, c])


def add_params(fig, ax, y_label=None, x_label=None, loc=None, title=None,
               filename="./results/plot_2_gaussian_output.png", showfig=False, savefig=True):
    """
    :param fig:
    :param ax:
    :param y_label: The y axis label.
    :param x_label: The x axis label.
    :param loc: can be a string or an integer specifying the legend location. default: None.
                    https://matplotlib.org/api/legend_api.html#matplotlib.legend.Legend
    :param title: str or None. The legend’s title. Default is no title (None).
    :param filename: Only used when savefig=True. The name of the figure to be saved
    :param showfig: Boolean. If true it will show the figure using matplotlib show method
    :param savefig: Boolean. If true it will save the figure with the name of filename parameter
    :return None:
    """
    # Figure parameters
    if loc is not None:
        fig.legend(loc=loc)
    if y_label is not None:
        ax.set_ylabel(y_label)
    if x_label is not None:
        ax.set_xlabel(x_label)
    if title is not None:
        ax.set_title(title)
    # save/show results
    if showfig:
        fig.show()
    if savefig:
        os.makedirs(os.path.split(filename)[0], exist_ok=True)
        fig.savefig(filename, transparent=True)


def get_trailing_number(s):
    """
    Search for a termination of a file name that has the ".csv" extension and that has a number at the end.
    It gives the number at the end of the file. This number can have any amount of digits.
    Example:
    x = get_trailing_number("my/path/to/file/any_43_start_name9872.csv")    # x = 9872
    y = get_trailing_number("my/path/to/file/any_43_start_name.csv")        # y = None
    z = get_trailing_number("my/path/to/file/any_43_start_name85498.txt")   # y = None
    :param s: The string to search for the specific term
    :return: The number located before the extension. None if there is no number.
    """
    m = re.search(r'\d+.csv$', s)  # I get only the end of the string (last number of any size and .csv extension)
    # splitext gets root [0] and extension [1] of the name.
    return int(os.path.splitext(m.group())[0]) if m else None


# ----------------
# Confusion Matrix
# ----------------


def plot_confusion_matrix(data, filename=None, library='plotly', axis_legends=None, showfig=False):
    if library == 'seaborn':
        fig, ax = plt.subplots()
        sns.heatmap(data,
                    annot=True,
                    linewidths=.5,
                    cbar=True,
                    )
        if filename is not None:
            fig.savefig(filename)
    elif library == 'plotly':
        z = data.values.tolist()
        if axis_legends is None:
            y = [str(j) for j in data.axes[0].tolist()]
            x = [str(i) for i in data.axes[1].tolist()]
        else:
            y = []
            x = []
            for j in data.axes[0].tolist():
                if isinstance(j, int):
                    y.append(axis_legends[j])
                elif isinstance(j, str):
                    y.append(j)
                else:
                    logger.critical("WTF?! should never have arrived here")
            for i in data.axes[1].tolist():
                if isinstance(i, int):
                    x.append(axis_legends[i])
                elif isinstance(i, str):
                    x.append(i)
                else:
                    logger.critical("WTF?! should never have arrived here")
        # fig = go.Figure(data=go.Heatmap(z=z, x=x, y=y))
        fig = ff.create_annotated_heatmap(z, x=x, y=y)
    if showfig:
        fig.show()


def confusion_matrix(y_pred_np, y_label_np, filename=None, axis_legends=None):
    categorical = (len(np.shape(y_label_np)) > 1)
    if categorical:
        y_pred_np = np.argmax(y_pred_np, axis=1)
        y_label_np = np.argmax(y_label_np, axis=1)
    y_pred_pd = pd.Series(y_pred_np, name='Predicted')
    y_label_pd = pd.Series(y_label_np, name='Actual')
    df = pd.crosstab(y_label_pd, y_pred_pd, rownames=['Actual'], colnames=['Predicted'], margins=True)
    if filename is not None:
        df.to_csv(filename)
    # plot_confusion_matrix(df, filename, library='plotly', axis_legends=axis_legends)
    return df

# ----------------
# Comparison
# ----------------


class SeveralMonteCarloComparison:

    def __init__(self, label, x, paths, round=2):
        """
        This class is used to compare several monte carlo runs done with cvnn.montecarlo.MonteCarlo class.
        MonteCarlo let's you compare different models between them but let's you not change other values like epochs.
        You can run as several MonteCarlo runs and then use SeveralMonteCarloComparison class to compare the results.

        Example of usage:

        ```
        # Run several Monte Carlo's
        for learning_rate in learning_rates:
            monte_carlo = RealVsComplex(complex_network)
            monte_carlo.run(x, y, iterations=iterations, learning_rate=learning_rate,
                            epochs=epochs, batch_size=batch_size, display_freq=display_freq,
                            shuffle=True, debug=debug, data_summary=dataset.summary())
        # Run self
        several = SeveralMonteCarloComparison('learning rate', x = learning_rates,
                                              paths = ["path/to/1st/run/run_data",
                                                       "path/to/2nd/run/run_data",
                                                       "path/to/3rd/run/run_data",
                                                       "path/to/4th/run/run_data"]
        several.box_plot(showfig=True)
        ```

        :label: string that describes what changed between each montecarlo run
        :x: List of the value for each monte carlo run wrt :label:.
        :paths: Full path to each monte carlo run_data saved file (Must end with run_data)
            NOTE: x and paths must be the same size
        """
        self.x_label = label
        if all([item.isdigit() for item in x]):
            self.x = list(map(int, x))
        elif all([item.replace(".", "", 1).isdigit() for item in x]):
            self.x = np.round(list(map(float, x)), round)
        else:
            self.x = x
        self.monte_carlo_runs = []
        for path in paths:
            self.monte_carlo_runs.append(MonteCarloAnalyzer(path=path))
        if not len(self.x) == len(self.monte_carlo_runs):
            logger.error("x ({0}) and paths ({1}) must be the same size".format(len(self.x),
                                                                                len(self.monte_carlo_runs)))

    def box_plot(self, key='test accuracy', library='plotly', step=-1, showfig=False, savefile=None):
        if library == 'plotly':
            self._box_plot_plotly(key=key, step=step, showfig=showfig, savefile=savefile)
        # TODO: https://seaborn.pydata.org/examples/grouped_boxplot.html
        else:
            logger.warning("Unrecognized library to plot " + library)
        return None

    def _box_plot_plotly(self, key='test accuracy', step=-1, showfig=False, savefile=None, extension=".svg"):
        # https://en.wikipedia.org/wiki/Box_plot
        # https://plot.ly/python/box-plots/
        # https://towardsdatascience.com/understanding-boxplots-5e2df7bcbd51
        # Median (Q2 / 50th Percentile): Middle value of the dataset. ex. median([1, 3, 3, 6, 7, 8, 9]) = 6
        # First quartile (Q1 / 25th Percentile): Middle value between the median and the min(dataset) = 1
        # Third quartile (Q3 / 75th Percentile): Middle value between the median and the max(dataset) = 9
        # Interquartile Range (IQR) = Q3 - Q1
        # Whishker: [Q1 - 1.5*IQR, Q3 + 1.5*IQR], whatever is out of this is an outlier.
        # suspected outlier: [Q1 - 3*IQR, Q3 + 3*IQR]
        savefig = False
        if savefile is not None:
            savefig = True

        steps = []
        for i in range(len(self.monte_carlo_runs)):
            if step == -1:
                steps.append(max(self.monte_carlo_runs[i].df.step))
            else:
                steps.append(step)

        fig = go.Figure()

        for i, mc_run in enumerate(self.monte_carlo_runs):
            df = mc_run.df
            networks_availables = df.network.unique()
            for color_index, net in enumerate(networks_availables):
                filter = [a == net and b == steps[i] for a, b in zip(df.network, df.step)]
                data = df[filter]
                fig.add_trace(go.Box(
                    y=data[key],
                    # x=[self.x[i]] * len(data[key]),
                    name=net.replace('_', ' ') + " " + str(self.x[i]),
                    whiskerwidth=0.2,
                    notched=True,       # confidence intervals for the median
                    fillcolor=add_transparency(DEFAULT_PLOTLY_COLORS[color_index], 0.5),
                    boxpoints='suspectedoutliers',      # to mark the suspected outliers
                    line=dict(color=DEFAULT_PLOTLY_COLORS[color_index]),
                    boxmean=True        # Interesting how sometimes it falls outside the box
                ))

        fig.update_layout(
            title=self.x_label + ' Box Plot',
            # xaxis=dict(title=self.x_label),
            yaxis=dict(
                title=key,
                autorange=True,
                showgrid=True,
                dtick=0.05,
            ),
            # boxmode='group',
            # boxgroupgap=0,
            # boxgap=0,
            showlegend=True
        )
        if not savefile.endswith('.html'):
            savefile += '.html'
        if savefig:
            os.makedirs(os.path.split(savefile)[0], exist_ok=True)
            plotly.offline.plot(fig,
                                filename=savefile, config={'scrollZoom': True, 'editable': True}, auto_open=showfig)
            fig.write_image(savefile.replace('.html', extension))
        elif showfig:
            fig.show(config={'editable': True})

    def save_pandas_csv_result(self, path, step=-1):
        # TODO: Check path
        if step == -1:
            step = max(self.monte_carlo_runs[0].df.step)    # TODO: Assert it's the same for all cases
        cols = ['train loss', 'test loss', 'train accuracy', 'test accuracy']
        for i, run in enumerate(self.monte_carlo_runs):
            df = run.df
            networks_availables = df.network.unique()
            for col, net in enumerate(networks_availables):
                filter = [a == net and b == step for a, b in zip(df.network, df.step)]
                data = df[filter].describe()
                data = data[cols]
                data.to_csv(path + net + "_" + self.x[i] + "_stats.csv")


class Plotter:

    def __init__(self, path, file_suffix="_results_fit.csv"):
        """
        This class manages the plot of results for a model train.
        It opens the csv files (test and train) saved during training and plots results as wrt each step saved.
        This class is generally used to plot accuracy and loss evolution during training.

        :path: Full path where the csv results are stored
        :file_suffix: (optional) let's you filter csv files to open only files that ends with the suffix.
            By default it opens every csv file it finds.
        """
        if not os.path.exists(path):
            logger.error("Path {} does not exist".format(path))
            sys.exit(-1)
        self.path = Path(path)
        if not file_suffix.endswith(".csv"):
            file_suffix += ".csv"
        self.file_suffix = file_suffix
        self.pandas_list = []
        self.labels = []
        self._csv_to_pandas()

    def _csv_to_pandas(self):
        """
        Opens the csv files as pandas dataframe and stores them in a list (self.pandas_list).
        Also saves the name of the file where it got the pandas frame as a label.
        This function is called by the constructor.
        """
        self.pandas_list = []
        self.labels = []
        files = os.listdir(self.path)
        files.sort()  # Respect the colors for the plot of Monte Carlo.
        # For ComplexVsReal Monte Carlo it has first the Complex model and SECOND the real one.
        # So ordering the files makes sure I open the Complex model first and so it plots with the same colours.
        # TODO: Think a better way without loosing generality (This sort is all done because of the ComplexVsReal case)
        for file in files:
            if file.endswith(self.file_suffix):
                self.pandas_list.append(pd.read_csv(self.path / file))
                self.labels.append(re.sub(self.file_suffix + '$', '', file).replace('_', ' '))

    def reload_data(self):
        """
        If data inside the working path has changed (new csv files or modified csv files),
        this function reloads the data to be plotted with that new information.
        """
        self._csv_to_pandas()

    def get_full_pandas_dataframe(self):
        """
        Merges every dataframe obtained from each csv file into a single dataframe.
        It adds the columns:
            - network: name of the train model
            - step: information of the step index
            - path: path where the information of the train model was saved (used as parameter with the constructor)
        :retun: pd.Dataframe
        """
        # https://pandas.pydata.org/pandas-docs/stable/user_guide/merging.html
        self._csv_to_pandas()
        length = len(self.pandas_list[0])
        for data_frame in self.pandas_list:  # TODO: Check if.
            if not length == len(data_frame):  # What happens if NaN? Can I cope not having same len?
                logger.error("Data frame length should have been {0} and was {1}".format(length, len(data_frame)))

        result = pd.DataFrame({
            'network': [self.get_net_name()] * length,
            # 'step': list(range(length)), # No longer needed, already added in base file
            'path': [self.path] * length
        })

        for data_frame, data_label in zip(self.pandas_list, self.labels):
            # data_frame.columns = [data_label + " " + str(col) for col in data_frame.columns]
            # concatenated = pd.concat(self.pandas_list, keys=self.labels)
            result = pd.concat([result, data_frame], axis=1, sort=False)
        return result

    def get_net_name(self):
        str_to_match = "_metadata.txt"
        for file in os.listdir(self.path):
            if file.endswith(str_to_match):
                # See that there is no need to open the file
                return re.sub(str_to_match + "$", '', file).replace('_', ' ')
        return "Name not found"

    # ====================
    #        Plot
    # ====================

    def plot_everything(self, reload=False, library='plotly', showfig=False, savefig=True, index_loc=None):
        if reload:
            self._csv_to_pandas()
        if not len(self.pandas_list) != 0:
            logger.error("Empty pandas list to plot")
            return None
        for key in ["loss", "accuracy"]:
            self.plot_key(key, reload=False, library=library, showfig=showfig, savefig=savefig, index_loc=index_loc)

    def plot_key(self, key='loss', reload=False, library='plotly', showfig=False, savefig=True, index_loc=None):
        if reload:
            self._csv_to_pandas()
        if library == 'matplotlib':
            self._plot_matplotlib(key=key, showfig=showfig, savefig=savefig, index_loc=index_loc)
        elif library == 'plotly':
            self._plot_plotly(key=key, showfig=showfig, savefig=savefig, index_loc=index_loc)
        else:
            logger.warning("Unrecognized library to plot " + library)

    def _plot_matplotlib(self, key='loss', showfig=False, savefig=True, index_loc=None, extension=".svg"):
        fig, ax = plt.subplots()
        ax.set_prop_cycle('color', DEFAULT_MATPLOTLIB_COLORS)
        title = None
        for i, data in enumerate(self.pandas_list):
            if title is not None:
                title += " vs. " + self.labels[i]
            else:
                title = self.labels[i]
            for k in data:
                if key in k:
                    if index_loc is not None:
                        if 'stats' in data.keys():
                            data = data[data['stats'] == 'mean']
                        else:
                            logger.warning("Warning: Trying to index an array without index")
                    ax.plot(data[k], 'o-', label=(k.replace(key, '') + self.labels[i]).replace('_', ' '))
        title += " " + key
        fig.legend(loc="upper right")
        ax.set_ylabel(key)
        ax.set_xlabel("step")
        ax.set_title(title)
        if showfig:
            fig.show()
        if savefig:
            fig.savefig(str(self.path / key) + "_matplotlib" + extension, transparent=True)

    def _plot_plotly(self, key='loss', showfig=False, savefig=True, func=min, index_loc=None, extension=".svg"):
        fig = go.Figure()
        annotations = []
        title = None
        for i, data in enumerate(self.pandas_list):
            if title is not None:
                title += " vs. " + self.labels[i]
            else:
                title = self.labels[i]
            j = 0
            for k in data:
                if key in k:
                    color = DEFAULT_PLOTLY_COLORS[j*len(self.pandas_list) + i]
                    j += 1
                    if index_loc is not None:
                        if 'stats' in data.keys():
                            data = data[data['stats'] == 'mean']
                        else:
                            logger.warning("Trying to index an array without index")
                    x = list(range(len(data[k])))
                    fig.add_trace(go.Scatter(x=x, y=data[k], mode='lines',
                                             name=(k.replace(key, '') + self.labels[i]).replace('_', ' '),
                                             line_color=color))
                    # Add points
                    fig.add_trace(go.Scatter(x=[x[-1]],
                                             y=[data[k].to_list()[-1]],
                                             mode='markers',
                                             name='last value',
                                             marker_color=color))
                    # Max/min points
                    func_value = func(data[k])
                    # ATTENTION! this will only give you first occurrence
                    func_index = data[k].to_list().index(func_value)
                    if func_index != len(data[k]) - 1:
                        fig.add_trace(go.Scatter(x=[func_index],
                                                 y=[func_value],
                                                 mode='markers',
                                                 name=func.__name__,
                                                 text=['{0:.2f}%'.format(func_value)],
                                                 textposition="top center",
                                                 marker_color=color))
                        # Min annotations
                        annotations.append(dict(xref="x", yref="y", x=func_index, y=func_value,
                                                xanchor='left', yanchor='middle',
                                                text='{0:.2f}'.format(func_value),
                                                font=dict(family='Arial',
                                                          size=14),
                                                showarrow=False, ay=-40))
                    # Right annotations
                    annotations.append(dict(xref='paper', x=0.95, y=data[k].to_list()[-1],
                                            xanchor='left', yanchor='middle',
                                            text='{0:.2f}'.format(data[k].to_list()[-1]),
                                            font=dict(family='Arial',
                                                      size=16),
                                            showarrow=False))
        title += " " + key
        fig.update_layout(annotations=annotations,
                          title=title,
                          xaxis_title='steps',
                          yaxis_title=key)
        if savefig:
            plotly.offline.plot(fig, filename=str(self.path / key) + ".html",
                                config={'scrollZoom': True, 'editable': True}, auto_open=showfig)
            fig.write_image(str(self.path / key) + "_plotly" + extension)
        elif showfig:
            fig.show(config={'editable': True})


class MonteCarloPlotter(Plotter):

    def __init__(self, path):
        file_suffix = "_statistical_result.csv"
        super().__init__(path, file_suffix=file_suffix)

    def plot_everything(self, reload=False, library='plotly', showfig=False, savefig=True, index_loc='mean'):
        # Rename this function to change index_loc default value
        super().plot_key(reload=False, library=library, showfig=showfig, savefig=savefig, index_loc=index_loc)

    def plot_key(self, key='test accuracy', reload=False, library='plotly', showfig=False, savefig=True,
                 index_loc='mean'):
        # Rename this function to change index_loc default value
        super().plot_key(key, reload, library, showfig, savefig, index_loc)

    def plot_distribution(self, key='test accuracy', showfig=False, savefig=True, title='', full_border=True):
        fig = go.Figure()
        for i, data in enumerate(self.pandas_list):
            x = data['step'].unique().tolist()
            x_rev = x[::-1]
            data_mean = data[data['stats'] == 'mean'][key].tolist()
            data_max = data[data['stats'] == 'max'][key].tolist()
            data_min = data[data['stats'] == 'min'][key][::-1].tolist()
            data_50 = data[data['stats'] == '50%'][key].tolist()
            data_25 = data[data['stats'] == '25%'][key][::-1].tolist()
            data_75 = data[data['stats'] == '75%'][key].tolist()
            # set_trace()
            if full_border:
                fig.add_trace(go.Scatter(
                    x=x + x_rev,
                    y=data_max + data_min,
                    fill='toself',
                    fillcolor=add_transparency(DEFAULT_PLOTLY_COLORS[i], 0.1),
                    line_color=add_transparency(DEFAULT_PLOTLY_COLORS[i], 0),
                    showlegend=True,
                    name=self.labels[i].replace('_', ' ') + " borders",
                ))
            fig.add_trace(go.Scatter(
                x=x + x_rev,
                y=data_75 + data_25,
                fill='toself',
                fillcolor=add_transparency(DEFAULT_PLOTLY_COLORS[i], 0.2),
                line_color=add_transparency(DEFAULT_PLOTLY_COLORS[i], 0),
                showlegend=True,
                name=self.labels[i].replace('_', ' ') + " interquartile",
            ))
            fig.add_trace(go.Scatter(
                x=x, y=data_mean,
                line_color=DEFAULT_PLOTLY_COLORS[i],
                name=self.labels[i].replace('_', ' ') + " mean",
            ))
            fig.add_trace(go.Scatter(
                x=x, y=data_50,
                line=dict(color=DEFAULT_PLOTLY_COLORS[i], dash='dash'),
                name=self.labels[i].replace('_', ' ') + " median",
            ))
        for label in self.labels:
            title += label.replace('_', ' ') + ' vs '
        title = title[:-3] + key

        fig.update_traces(mode='lines')
        fig.update_layout(title=title, xaxis_title='steps', yaxis_title=key)

        if savefig:
            os.makedirs(str(self.path / "plots/lines/"), exist_ok=True)
            plotly.offline.plot(fig,
                                filename=str(self.path / ("plots/lines/montecarlo_" + key.replace(" ", "_"))) + ".html",
                                config={'scrollZoom': True, 'editable': True}, auto_open=showfig)
            fig.write_image(str(self.path / ("plots/lines/montecarlo_" + key.replace(" ", "_"))) + ".svg")
        elif showfig:
            fig.show(config={'editable': True})

    def plot_train_vs_test(self, key='loss', showfig=False, savefig=True, median=False):
        # TODO: Change the extension as a variable like matplotlib
        fig = go.Figure()
        # test plots
        label = 'mean'
        if median:
            label = '50%'
        for i, data in enumerate(self.pandas_list):
            x = data['step'].unique().tolist()
            data_mean_test = data[data['stats'] == label]["test " + key].tolist()
            fig.add_trace(go.Scatter(
                x=x, y=data_mean_test,
                line_color=DEFAULT_PLOTLY_COLORS[i],
                name=self.labels[i] + " test",
            ))
            data_mean_train = data[data['stats'] == label]["train " + key].tolist()
            fig.add_trace(go.Scatter(
                x=x, y=data_mean_train,
                line_color=DEFAULT_PLOTLY_COLORS[i + len(self.pandas_list)],
                name=self.labels[i].replace("_", " ") + " train ",
            ))
        title = "train and test " + key + " " + label.replace("50%", "median")
        fig.update_traces(mode='lines')
        fig.update_layout(title=title, xaxis_title='steps', yaxis_title=key)

        if savefig:
            os.makedirs(self.path / "plots/lines/", exist_ok=True)
            plotly.offline.plot(fig,
                                filename=str(self.path / ("plots/lines/montecarlo_" + key.replace(" ", "_")))
                                         + "_" + label.replace("50%", "median") + ".html",
                                config={'scrollZoom': True, 'editable': True}, auto_open=showfig)
            fig.write_image(str(self.path / ("plots/lines/montecarlo_" + key.replace(" ", "_"))) + "_" + label.replace("50%", "median") + ".svg")
        elif showfig:
            fig.show(config={'editable': True})


class MonteCarloAnalyzer:

    def __init__(self, df=None, path=None):
        self.confusion_matrix = []
        if path is not None and df is not None:  # I have data and the place where I want to save it
            self.df = df  # DataFrame with all the data
            self.path = Path(path)
            self.df.to_csv(self.path / "run_data.csv")  # Save the results for latter use
        elif path is not None and df is None:  # Load df from Path
            if not path.endswith('.csv'):
                path += '.csv'
            self.df = pd.read_csv(Path(path))   # Path(__file__).parents[1].absolute() /
            self.path = Path(os.path.split(path)[0])  # Keep only the path and not the filename
        elif path is None and df is not None:  # Save df into default path
            self.path = create_folder("./log/montecarlo/")
            self.df = df  # DataFrame with all the data
            self.df.to_csv(self.path / "run_data.csv")  # Save the results for latter use
        else:  # I have nothing
            self.path = create_folder("./log/montecarlo/")
            self.df = pd.DataFrame()
        self.plotable_info = ['train loss', 'test loss', 'train accuracy', 'test accuracy']  # TODO: Consider delete
        self.monte_carlo_plotter = MonteCarloPlotter(self.path)

    def set_df(self, df, conf_mat=None):
        self.df = df                                # DataFrame with all the data
        self.df.to_csv(self.path / "run_data.csv")  # Save the results for latter use
        if conf_mat is not None:
            for i in range(len(conf_mat)):
                mat = conf_mat[i]["matrix"]
                group = mat.groupby(mat.index)
                self.confusion_matrix.append({"name": conf_mat[i]["name"], "matrix": group.mean()})
        self.save_stat_results()
        self.monte_carlo_plotter.reload_data()

    def save_stat_results(self):
        # save csv file for each network with 4 columns
        networks_availables = self.df.network.unique()
        for net in networks_availables:
            data = self.df[self.df.network == net]
            cols = ['train loss', 'test loss', 'train accuracy', 'test accuracy']
            frames = []
            keys = []
            for step in data.step.unique():
                frames.append(data[data.step == step][cols].describe())
                keys.append(step)
            data_to_save = pd.concat(frames, keys=keys, names=['step', 'stats'])
            data_to_save.to_csv(self.path / (net + "_statistical_result.csv"))
        # Save confusion matrix
        for i in range(len(self.confusion_matrix)):
            self.confusion_matrix[i]["matrix"].to_csv(self.path / (self.confusion_matrix[i]["name"]
                                                                   + "_confusion_matrix.csv"))

    # ------------
    # Plot methods
    # ------------

    def do_all(self):
        self.monte_carlo_plotter.plot_train_vs_test(key='loss')
        self.monte_carlo_plotter.plot_train_vs_test(key='accuracy')
        self.monte_carlo_plotter.plot_train_vs_test(key='loss', median=True)
        self.monte_carlo_plotter.plot_train_vs_test(key='accuracy', median=True)

        for key in ['train loss', 'test loss', 'train accuracy', 'test accuracy']:
            self.plot_3d_hist(key=key)
            self.monte_carlo_plotter.plot_distribution(key=key)
            self.box_plot(key=key)

            for lib in ['matplotlib', 'seaborn']:  # 'plotly',
                self.plot_histogram(key=key, library=lib, showfig=False, savefig=True)

    def box_plot(self, step=-1, key='test accuracy', showfig=False, savefig=True):
        fig = go.Figure()
        if step == -1:
            step = max(self.df.step)
        networks_availables = self.df.network.unique()
        for col, net in enumerate(networks_availables):
            filter = [a == net and b == step for a, b in zip(self.df.network, self.df.step)]
            data = self.df[filter]
            fig.add_trace(go.Box(
                y=data[key],
                # x=[self.x[i]] * len(data[key]),
                name=net.replace('_', ' '),
                whiskerwidth=0.2,
                notched=True,  # confidence intervals for the median
                fillcolor=add_transparency(DEFAULT_PLOTLY_COLORS[col], 0.5),
                boxpoints='suspectedoutliers',  # to mark the suspected outliers
                line=dict(color=DEFAULT_PLOTLY_COLORS[col]),
                boxmean=True  # Interesting how sometimes it falls outside the box
            ))
        fig.update_layout(
            title='Montecarlo Box Plot ' + key,
            xaxis=dict(
                title="network",
            ),
            yaxis=dict(
                title=key,
                autorange=True,
                showgrid=True,
                dtick=0.05,
            ),
            # boxmode='group',
            # boxgroupgap=0,
            # boxgap=0,
            showlegend=False
        )
        if savefig:
            os.makedirs(self.path / "plots/box_plot/", exist_ok=True)
            plotly.offline.plot(fig,
                                filename=str(self.path / ("plots/box_plot/montecarlo_" + key.replace(" ", "_") + "_box_plot.html")),
                                config={'scrollZoom': True, 'editable': True}, auto_open=showfig)
            fig.write_image(str(self.path / ("plots/box_plot/montecarlo_" + key.replace(" ", "_") + "_box_plot.svg")))
        elif showfig:
            fig.show(config={'editable': True})

    def show_plotly_table(self):
        # TODO: Not yet debugged
        values = [key for key in self.df.keys()]
        fig = go.Figure(data=[go.Table(
            header=dict(values=list(self.df.columns),
                        fill_color='paleturquoise',
                        align='left'),
            cells=dict(values=[self.df.values.tolist()],
                       fill_color='lavender',
                       align='left'))
        ])
        fig.show(config={'editable': True})

    def plot_3d_hist(self, steps=None, key='test accuracy', title=''):
        # https://stackoverflow.com/questions/60398154/plotly-how-to-make-a-3d-stacked-histogram/60403270#60403270
        # https://plot.ly/python/v3/3d-filled-line-plots/
        # https://community.plot.ly/t/will-there-be-3d-bar-charts-in-the-future/1045/3
        # https://matplotlib.org/examples/mplot3d/bars3d_demo.html
        if steps is None:
            # steps = [int(x) for x in np.linspace(min(self.df.step), max(self.df.step), 6)]
            steps = [int(x) for x in np.logspace(min(self.df.step), np.log2(max(self.df.step)), 8, base=2)]
            # steps = [int(x) for x in np.logspace(min(self.df.step), np.log10(max(self.df.step)), 8)]
            steps[0] = 0
        networks_availables = self.df.network.unique()
        cols = ['step', key]
        fig = go.Figure()
        for step in steps:  # TODO: verify steps are in df
            for i, net in enumerate(networks_availables):
                filter = [a == net and b == step for a, b in zip(self.df.network, self.df.step)]
                data_to_plot = self.df[filter][cols]
                # https://stackoverflow.com/a/60403270/5931672
                counts, bins = np.histogram(data_to_plot[key], bins=10, density=False)
                counts = list(np.repeat(counts, 2).tolist())  # I do this to stop pycharm warning
                counts.insert(0, 0)
                counts.append(0)
                bins = np.repeat(bins, 2)

                fig.add_traces(go.Scatter3d(x=[step] * len(counts), y=bins, z=counts,
                                            mode='lines', name=net.replace("_", " ") + "; step: " + str(step),
                                            surfacecolor=add_transparency(DEFAULT_PLOTLY_COLORS[i], 0),
                                            # surfaceaxis=0,
                                            line=dict(color=DEFAULT_PLOTLY_COLORS[i], width=4)
                                            )
                               )
                verts, tri = triangulate_histogram([step] * len(counts), bins, counts)
                x, y, z = verts.T
                I, J, K = tri.T
                fig.add_traces(go.Mesh3d(x=x, y=y, z=z, i=I, j=J, k=K, color=DEFAULT_PLOTLY_COLORS[i], opacity=0.4))
        for net in networks_availables:
            title += net + ' '
        title += key + " comparison"
        fig.update_layout(title=title,
                          scene=dict(
                              xaxis=dict(title='step'),
                              yaxis=dict(title=key),
                              zaxis=dict(title='counts'),
                              xaxis_type="log"))
        os.makedirs(self.path / "plots/histogram/", exist_ok=True)
        plotly.offline.plot(fig,
                            filename=str(self.path / ("plots/histogram/montecarlo_" + key.replace(" ", "_") + "_3d_histogram.html")),
                            config={'scrollZoom': True, 'editable': True}, auto_open=False)

    def plot_histogram(self, key='test accuracy', step=-1, library='plotly', showfig=False, savefig=True, title='', extension=".svg"):
        if library == 'matplotlib':
            self._plot_histogram_matplotlib(key=key, step=step, showfig=showfig, savefig=savefig, title=title, extension=extension)
        elif library == 'plotly':
            self._plot_histogram_plotly(key=key, step=step, showfig=showfig, savefig=savefig, title=title)
        elif library == 'seaborn':
            self._plot_histogram_seaborn(key=key, step=step, showfig=showfig, savefig=savefig, title=title)
        else:
            logger.warning("Warning: Unrecognized library to plot " + library)
            return None

    def _plot_histogram_matplotlib(self, key='test accuracy', step=-1,
                                   showfig=False, savefig=True, title='', extension=".svg"):
        fig, ax = plt.subplots()
        ax.set_prop_cycle('color', DEFAULT_MATPLOTLIB_COLORS)
        bins = np.linspace(0, 1, 501)
        min_ax = 1.0
        max_ax = 0.0
        networks_availables = self.df.network.unique()
        if step == -1:
            step = max(self.df.step)
        for net in networks_availables:
            filter = [a == net and b == step for a, b in zip(self.df.network, self.df.step)]
            data = self.df[filter]  # Get only the data to plot
            ax.hist(data[key], bins, alpha=0.5, label=net.replace("_", " "))
            min_ax = min(min_ax, min(data[key]))
            max_ax = max(max_ax, max(data[key]))
        title += key + " histogram"
        ax.axis(xmin=min_ax - 0.01, xmax=max_ax + 0.01)
        add_params(fig, ax, x_label=key, y_label="occurances", title=title, loc='upper right',
                   filename=self.path / ("plots/histogram/montecarlo_" + key.replace(" ", "_") + "_matplotlib" + extension), showfig=showfig, savefig=savefig)
        return fig, ax

    def _plot_histogram_plotly(self, key='test accuracy', step=-1, showfig=False, savefig=True, title=''):
        networks_availables = self.df.network.unique()
        if step == -1:
            step = max(self.df.step)
        hist_data = []
        group_labels = []
        for net in networks_availables:
            title += net + ' '
            filter = [a == net and b == step for a, b in zip(self.df.network, self.df.step)]
            data = self.df[filter]  # Get only the data to plot
            hist_data.append(data[key].to_list())
            group_labels.append(net.replace("_", " "))
            # fig.add_trace(px.histogram(np.array(data[key]), marginal="box"))
            # fig.add_trace(go.Histogram(x=np.array(data[key]), name=net))
        fig = ff.create_distplot(hist_data, group_labels, bin_size=0.01)  # https://plot.ly/python/distplot/
        title += key + " comparison"

        # Overlay both histograms
        fig.update_layout(barmode='overlay')
        # Reduce opacity to see both histograms
        fig.update_traces(opacity=0.75)
        fig.update_layout(title=title.replace('_', ' '),
                          xaxis_title=key)
        if savefig:
            os.makedirs(self.path / "plots/histogram/", exist_ok=True)
            plotly.offline.plot(fig,
                                filename=str(self.path / ("plots/histogram/montecarlo_" + key.replace(" ", "_") + "_histogram.html")),
                                config={'scrollZoom': True, 'editable': True}, auto_open=showfig)
            fig.write_image(str(self.path / ("plots/histogram/montecarlo_" + key.replace(" ", "_") + "plotly_histogram.svg")))
        elif showfig:
            fig.show(config={'editable': True})
        return fig

    def _plot_histogram_seaborn(self, key='test accuracy', step=-1,
                                showfig=False, savefig=True, title='', extension=".svg"):
        fig = plt.figure()
        bins = np.linspace(0, 1, 501)
        min_ax = 1.0
        max_ax = 0.0
        ax = None
        networks_availables = self.df.network.unique()
        if step == -1:
            step = max(self.df.step)
        for net in networks_availables:
            filter = [a == net and b == step for a, b in zip(self.df.network, self.df.step)]
            data = self.df[filter]  # Get only the data to plot
            ax = sns.distplot(data[key], bins, label=net.replace("_", " "))
            min_ax = min(min_ax, min(data[key]))
            max_ax = max(max_ax, max(data[key]))
        title += " " + key
        ax.axis(xmin=min_ax - 0.01, xmax=max_ax + 0.01)
        add_params(fig, ax, x_label=key, title=title, loc='upper right',
                   filename=self.path / ("plots/histogram/montecarlo_" + key.replace(" ", "_") + "_seaborn" + extension),
                   showfig=showfig, savefig=savefig)
        return fig, ax


__author__ = 'J. Agustin BARRACHINA'
__version__ = '0.1.23'
__maintainer__ = 'J. Agustin BARRACHINA'
__email__ = 'joseagustin.barra@gmail.com; jose-agustin.barrachina@centralesupelec.fr'
