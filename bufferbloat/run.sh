#!/bin/bash

# Note: Mininet must be run as root.  So invoke this shell script
# using sudo.

mn -c # começa deletando o antigo

iperf_port=5001

for qsize in 20 100; do
    dir=bb-q$qsize

    # TODO: Run bufferbloat.py here...
    python3 bufferbloat.py --bw-net=1.5 --bw-host=1000 --delay=5 --dir=$dir --maxq=$qsize --time=90

    # TODO: Ensure the input file names match the ones you use in
    # bufferbloat.py script.  Also ensure the plot file names match
    # the required naming convention when submitting your tarball.
    python3 plot_queue.py -f $dir/q.txt -o reno-buffer-q$qsize.png
    python3 plot_ping.py -f $dir/ping.txt -o reno-rtt-q$qsize.png
done
