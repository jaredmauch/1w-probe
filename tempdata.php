<?php

$options = array(
 "--step", "300",            // Use a step-size of 5 minutes
 "--start", "-12 months",     // this rrd started 6 months ago
 "DS:temp_c:GAUGE:900:0:U",
 "DS:temp_f:GAUGE:900:0:U",
 "RRA:AVERAGE:0.5:1:288",
 "RRA:AVERAGE:0.5:12:168",
 "RRA:AVERAGE:0.5:228:365",
 );

$ret = rrd_create("temps.rrd", $options);
if (! $ret) {
 echo "<b>Creation error: </b>".rrd_error()."\n";
}

?>

<?php
$db = new SQLite3('tempsensor.db', SQLITE3_OPEN_READONLY);

$now_time_t = time();
# CREATE TABLE temps (probe text not null, time_t integer, temp real);

# twelve hours ago
#$twelve_ago = $now_time_t - (60*60*12);
$twelve_ago=0;

$sql = "SELECT * FROM temps WHERE time_t > $twelve_ago AND probe='/sys/bus/w1/devices/28-000006153bb4'";
#print $sql;
#print "\n";
$results = $db->query($sql);

#print $twelve_ago;
#print "\n";

while ($row = $results->fetchArray()) {
	$tempf = ($row[2]* 9)/5 +32;
#	print "$row[0] $row[1] $row[2] $tempf\n";
##	print "$row[1]:$row[2]:$tempf\n";
    $ret = rrd_update("temps.rrd", array("$row[1]:$row[2]:$tempf"));
#    var_dump($row)o
}
?>

<?php

create_graph("temps-hour.gif", "-1h", "Hourly temp");
create_graph("temps-day.gif", "-1d", "Daily temp");
create_graph("temps-week.gif", "-1w", "Weekly temp");
create_graph("temps-month.gif", "-1m", "Monthly temp");
create_graph("temps-year.gif", "-1y", "Yearly temp");

function create_graph($output, $start, $title) {
  $options = array(
    "--slope-mode",
    "--start", $start,
    "--title=$title",
    "--vertical-label=heat value",
    "--lower=0",
    "DEF:temp_f=temps.rrd:temp_f:AVERAGE",
    "CDEF:cdef_temp_f=temp_f",
    "AREA:temp_f#00FF00:warmth level",
    "GPRINT:cdef_temp_f:MIN: Min\\: %6.2lf",
    "GPRINT:cdef_temp_f:MAX: Max\\: %6.2lf\\n",
    "GPRINT:cdef_temp_f:AVERAGE: Avg\\: %6.2lf",

  );

  $ret = rrd_graph($output, $options);
  if (! $ret) {
    echo "<b>Graph error: </b>".rrd_error()."\n";
  }
}
?>

