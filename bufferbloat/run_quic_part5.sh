#!/bin/bash

# Note: Mininet must be run as root.  So invoke this shell script
# using sudo.

# mn -c # começa deletando o antigo

iperf_port=4433

for qsize in 20 100; do
    
    mn -c
    dir=bb-quic-part5-q$qsize

    # TODO: Run bufferbloat.py here...
    python3 bufferbloat_quic_part5.py --bw-net=1.5 --bw-host=1000 --delay=5 --dir=$dir --maxq=$qsize --time=90

    # TODO: Ensure the input file names match the ones you use in
    # bufferbloat.py script.  Also ensure the plot file names match
    # the required naming convention when submitting your tarball.
    python3 plot_queue.py -f $dir/q.txt -o quic-part5-buffer-q$qsize.png
    #python3 plot_ping.py -f $dir/ping.txt -o quic-part5-rtt-q$qsize.png
    
    
done
