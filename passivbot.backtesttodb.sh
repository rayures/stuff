#!/bin/bash

#usage: 
# create `passivbotresults.symbollist.txt` file with the symbols to test
# adjust variable in this file where needed
# run with `bash passivbot.backtesttodb.sh`

version="520"
basepath="/home/v520"

#sqlite
dbpath=$basepath
dbname="passivbotresults"

#passivbot
symbollist="$basepath/passivbotresults.symbollist.txt"
pbrlist="0.1 0.15 1.0 1.5 2.0 2.1 2.2 2.3 2.4 2.5 2.6 2.7 2.8 2.9 3.0"
start1="2021-05-01"
end1="2021-12-21"
#config1=""$basepath"v"$version"/passivbot/backtests/multi.json"
config1="/home/v510/passivbot/backtests/binance/SOLUSDT/plots/2021-12-07T010835/live_config.json"

#_____

database=""$dbpath"/"$dbname".db"
sql="sqlite3 $database"
output=""$basepath"/passivbotresults.temp.output.txt"


cd "$basepath/"

#creat output file


#create db and table
$sql "CREATE TABLE RESULTS (            id integer primary key,
                                        symbol text,
                                        pbrlong text,
                                        pbrshort text,
                                        start text,
                                        end test,
                                        nodays real,
                                        totalgain real,
                                        adg real,
                                        bkr real,
                                        profit real,
                                        loss real,
                                        pacmeanlong real,
                                        pacmeanshort real,
                                        avgfills real,
                                        maxhstucklong real,
                                        maxhstuckshort real,
                                        version real,
                                        config real
);"


cd ""$basepath"/passivbot/"

while IFS="" read -r p || [ -n "$p" ]
 do 
    symbol1=$(echo $p | cut -d"/" -f 2)    
    for pbr1 in $pbrlist
     do
        printf "%s\n" "start: $start1" > $output
        printf "%s\n" "end: $end1" >> $output
        echo "symbol:" $symbol1
        printf "%s\n" "$symbol1" >> $output
        echo "pbr:" $pbr1
        #run backtest and log to output file
        python3 backtest.py -u binance_01 -s "$symbol1" -sd "$start1" -ed "$end1" -lw "$pbr1" $config1 | tee  >( tail -n 120 >> $output)
        sleep 2
        #---
        
        #pump all into vars:
        #yes, it gives errors, but it still works.
        symbol=$symbol1
        #pbrlong=$(grep -Pzo "(?<=pbr long: )(\d*\.\d*|\d*)" $output)
        pbrlong=$pbr1
        #pbrshort=$(grep -Pzo "(?<=pbr short: )(\d*\.\d*|\d*)" $output)
        pbrshort=$pbr1
        start=$start1
        end=$end1
        nodays=$(grep -Pzo "(?<=n_days )(\d*\.\d*)" $output)
        totalgain=$(grep -Pzo "(?<=\| Total gain percentage              \| )(\d*\.\d*)" $output)
        adg=$(grep -Pzo "(?<=\| Average daily gain percentage      \| )(\d*\.\d*)" $output)
        bkr=$(grep -Pzo "(?<=\| Closest bankruptcy percentage      \| )(\d*\.\d*)" $output)
        profit=$(grep -Pzo "(?<=\| Profit sum                         \| )(\d*\.\d*)" $output)
        loss=$(grep -Pzo "(?<=\| Loss sum                           \| )(\W\d*\.\d*)" $output)
        pacmeanlong=$(grep -Pzo "(?<=\| Price action distance mean long    \| )(\d*\.\d*)" $output)
        pacmeanshort=$(grep -Pzo "(?<=\| Price action distance mean short   \| )(\d*\.\d*)" $output)
        avgfills=$(grep -Pzo "(?<=\| Average n fills per day            \| )(\d*\.\d*)" $output)
        maxhstucklong=$(grep -Pzo "(?<=\| Max hours stuck \(long\)             \| )(\d*\.\d*)" $output)
        maxhstuckshort=$(grep -Pzo "(?<=\| Max hours stuck \(short\)            \| )(\d*\.\d*)" $output)
        config=$(grep -Pzo  "(?s)({')(.*)(}})" $output)
        config=${config//\'/\"} #replace ' with " before insert in db
        version=$version

        #store it all into a db        
        $sql "INSERT INTO RESULTS (symbol, pbrlong, pbrshort, start, end, nodays, totalgain, adg, bkr, profit, loss, pacmeanlong, pacmeanshort, avgfills, maxhstucklong, maxhstuckshort, version, config)
                VALUES ('$symbol',
                        '$pbrlong',
                        '$pbrshort',
                        '$start',
                        '$end',
                        '$nodays',
                        '$totalgain',
                        '$adg',
                        '$bkr',
                        '$profit',
                        '$loss',
                        '$pacmeanlong',
                        '$pacmeanshort',
                        '$avgfills',
                        '$maxhstucklong',
                        '$maxhstuckshort',
                        '$version',
                        '${config}');"
        printf "%s\n"
     done
    
 done < $symbollist
