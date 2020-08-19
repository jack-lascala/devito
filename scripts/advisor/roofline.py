"""
Generate a roofline for the Intel Advisor ``project``.

This module has been partly extracted from the examples directory of Intel Advisor 2018.
"""

import advisor

import click

import math
import pandas as pd
import numpy as np
import matplotlib
from matplotlib.ticker import ScalarFormatter
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa

# Use fancy plot colors
plt.style.use('seaborn-darkgrid')


@click.command()
# Required arguments
@click.option('--name', '-n', required=True, help='The name of the generated roofline.')
@click.option('--project', '-o', required=True,
              help='The directory of the Intel Advisor project containing '
                   'a roofline analysis.')
# Optional arguments
@click.option('--scale', type=float, help='Specify by how much should the roofs be '
                                          'scaled down due to using fewer cores than '
                                          'available (e.g., when running on a single '
                                          'socket).')
@click.option('--precision', type=click.Choice(['SP', 'DP', 'all']),
              help='Arithmetic precision.', default='SP')
@click.option('--overview', 'mode', flag_value='overview', default=True)
@click.option('--top-loops', 'mode', flag_value='top-loops')
def roofline(name, project, scale, precision, mode):
    pd.options.display.max_rows = 20

    project = advisor.open_project(str(project))
    data = project.load(advisor.SURVEY)
    rows = [{col: row[col] for col in row} for row in data.bottomup]
    roofs = data.get_roofs()

    full_df = pd.DataFrame(rows).replace('', np.nan)

    # Narrow down the columns to those of interest
    df = full_df[analysis_columns]

    df.self_ai = df.self_ai.astype(float)
    df.self_gflops = df.self_gflops.astype(float)
    df.self_time = df.self_time.astype(float)

    # Add time weight column
    loop_total_time = df.self_time.sum()
    df['percent_weight'] = df.self_time / loop_total_time * 100

    fig, ax = plt.subplots()
    key = lambda roof: roof.bandwidth if 'bandwidth' not in roof.name.lower() else 0
    max_compute_roof = max(roofs, key=key)
    max_compute_bandwidth = max_compute_roof.bandwidth / math.pow(10, 9)  # as GByte/s
    max_compute_bandwidth /= scale  # scale down as requested by the user

    key = lambda roof: roof.bandwidth if 'bandwidth' in roof.name.lower() else 0
    max_memory_roof = max(roofs, key=key)
    max_memory_bandwidth = max_memory_roof.bandwidth / math.pow(10, 9)  # as GByte/s
    max_memory_bandwidth /= scale  # scale down as requested by the user

    # Parameters to center the chart
    ai_min = 2**-5
    ai_max = 2**5
    gflops_min = 2**0
    width = ai_max

    for roof in roofs:
        # by default drawing multi-threaded roofs only
        if 'single-thread' not in roof.name:
            # memory roofs
            if 'bandwidth' in roof.name.lower():
                bandwidth = roof.bandwidth / math.pow(10, 9)  # as GByte/s
                bandwidth /= scale  # scale down as requested by the user
                # y = banwidth * x
                x1, x2 = 0, min(width, max_compute_bandwidth / bandwidth)
                y1, y2 = 0, x2 * bandwidth
                label = '{} {:.0f} GB/s'.format(roof.name, bandwidth)
                ax.plot([x1, x2], [y1, y2], '-', label=label)

            # compute roofs
            elif precision == 'all' or precision in roof.name:
                bandwidth = roof.bandwidth / math.pow(10, 9)  # as GFlOPS
                bandwidth /= scale  # scale down as requested by the user
                x1, x2 = max(bandwidth / max_memory_bandwidth, 0), width
                y1, y2 = bandwidth, bandwidth
                label = '{} {:.0f} GFLOPS'.format(roof.name, bandwidth)
                ax.plot([x1, x2], [y1, y2], '-', label=label)

    # drawing points using the same ax
    ax.set_xscale('log', basex=2)
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.set_yscale('log', basey=2)
    ax.yaxis.set_major_formatter(ScalarFormatter())

    if mode == 'overview':
        # Only display the overall GFLOPS and arithmetic intensity of the program
        ax.plot(data.metrics.total_ai, data.metrics.total_gflops, 'o', color='black')
    elif mode == 'top-loops':
        # Display the most costly loop followed by loops with same order of magnitude
        max_self_time = df.self_time.max()
        top_df = df[(max_self_time / df.self_time < 10) & (max_self_time / df.self_time >= 1)]
        ax.plot(top_df.self_ai, top_df.self_gflops, 'o', color='black')

    # make sure axes start at 1
    ax.set_ylim(ymin=gflops_min)
    ax.set_xlim(xmin=ai_min, xmax=ai_max)

    ax.set_xlabel('Arithmetic intensity (FLOP/Byte)')
    ax.set_ylabel('Performance (GFLOPS)')

    plt.legend(loc='lower right', fancybox=True, prop={'size': 7})

    # saving the chart in PDF format
    plt.savefig('%s.pdf' % name)


analysis_columns = [
        'loop_name',
        'self_ai',
        'self_gflops',
        'self_time',
        ]

if __name__ == '__main__':
    roofline()
