#!bash

basedir=exp4

rm -r Results/$basedir/
mkdir Results/$basedir/
cp trafficTrace.csv Results/$basedir/

for alpha in 0.0625 0.125 0.25 0.5 1.0 2.0 4.0 8.0 16.0 32.0
do
 for beta in 12.5 25.0 50.0 100.0 200.0 400.0
 do
  echo $alpha, $beta
  echo "target,alpha,beta,soft" > PIcontroller.csv
  echo 0.02,$alpha,$beta,1 >> PIcontroller.csv
  python3 CommunicationRO.py --ipaddress 10.0.27.12 > RO.txt &
  python3 CommunicationRA.py --ipaddress 10.0.27.12 > RA.txt &
  sudo docker run -it --rm --network host -e LENGTH=86400 -e IP_PYTHON=10.0.27.12 -e separate_ra=1 gitlab.ilabt.imec.be:4567/idlab-nokia/dynamicsim:selection_RO_or_RA_RO
  gnuplot plotRARO.gnuplot
  directory="a"$alpha"b"$beta
  echo $directory
  mkdir Results/$basedir/$directory
  cp PIcontroller.csv R?.txt *.png Results/$basedir/$directory
  killall python3
  sleep 30
 done
done

