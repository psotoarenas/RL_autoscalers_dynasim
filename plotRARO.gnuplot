#set terminal wxt 1
set term png
set output "work_CPU.png"
set multiplot layout 2, 1;
set xlabel "time [sec]"
set ylabel "work [CPUs]"
set yrange [0:8]
plot "RA.txt" u ($2/300) w l notitle
set xlabel "time [sec]"
set ylabel "number of CPUs"
set yrange [0:12]
plot "RO.txt" u 1 "MS: %lf, Cpu Usage: %lf, Overflow: %lf, Latency: %lf" w l notitle
unset multiplot

#set terminal wxt 2
set term png
set output "load_overflow.png"
set xlabel "time [sec]"
set ylabel "load & overflow"
set yrange [0.0:2.5]
plot "RO.txt" u 2 "MS: %lf, Cpu Usage: %lf, Overflow: %lf, Latency: %lf" w l title "CPUload" , \
     "RO.txt" u 3 "MS: %lf, Cpu Usage: %lf, Overflow: %lf, Latency: %lf" w l title "Overflow"

#set terminal wxt 3
set term png
set output "latency.png"
set xlabel "time [sec]"
set ylabel "latency [sec]"
#set yrange [1:10000]
set yrange [0.0:0.1]
#set logscale y
plot "RO.txt" u 4 "MS: %lf, Cpu Usage: %lf, Overflow: %lf, Latency: %lf" w l notitle


