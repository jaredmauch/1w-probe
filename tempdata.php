<?php

chdir('/var/www/html');

# rrd default options
$options = array(
	"--step", "60",            // Use a step-size of 60 seconds
	"--start", "-1y",     // this rrd started 6 months ago
	"DS:temp_c:GAUGE:300:0:U",
	"DS:temp_f:GAUGE:300:0:U",
	"RRA:AVERAGE:0.5:1:288",
	"RRA:AVERAGE:0.5:12:168",
	"RRA:AVERAGE:0.5:228:365",
	);

$db = new SQLite3('/home/pi/1w-probe/tempsensor.db', SQLITE3_OPEN_READONLY);
if (method_exists($db, 'busyTimeout')) $db->busyTimeout(10000);

$now_time_t = time();
# CREATE TABLE temps (probe text not null, time_t integer, temp real);

# twelve hours ago
$twelve_ago = $now_time_t - (60*60*24*180);
#
#$twelve_ago=0;

# fetch a unique list of the probes
$probe_sql = "select distinct probe from temps";
# run the query
$results = $db->query($probe_sql);

$probelist = array();
# push these unique probes into $probelist array
while ($row = $results->fetchArray()) {
	# push probe path into array $probelist
	array_push($probelist, $row[0]);
}

# iterate through probes creating graphs
foreach ($probelist as &$probe_path) {

	$ret = rrd_create("temps.rrd", $options);
	if (! $ret) {
		echo "<b>Creation error: </b>".rrd_error()."\n";
	}

	$sql = "SELECT * FROM temps WHERE probe='$probe_path'";
	#print $sql;
	#print "\n";
$results = $db->query($sql);

#print $twelve_ago;
#print "\n";

	while ($row = $results->fetchArray()) {
		$tempf = ($row[2]* 9)/5 +32;
#		print "$row[0] $row[1] $row[2] $tempf\n";
#		print "$row[1]:$row[2]:$tempf\n";
		$ret = rrd_update("temps.rrd", array("$row[1]:$row[2]:$tempf"));
#		var_dump($row)
	}

	$prefix = strrpos($probe_path, "/");
	$probe_prefix = substr($probe_path, $prefix+1);
#	print $probe_prefix . "\n";
	create_graph($probe_prefix."-temps-hour.gif", "-1h", "Hourly temp");
	create_graph($probe_prefix."-temps-day.gif", "-1d", "Daily temp");
	create_graph($probe_prefix."-temps-week.gif", "-1w", "Weekly temp");
	create_graph($probe_prefix."-temps-month.gif", "-1m", "Monthly temp");
	create_graph($probe_prefix."-temps-year.gif", "-1y", "Yearly temp");
}

# function to create a graphic 
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
		"GPRINT:cdef_temp_f:LAST: Current\\: %6.2lf",
	);

	$ret = rrd_graph($output, $options);
	if (! $ret) {
		echo "<b>Graph error: </b>".rrd_error()."\n";
	}
}

?>
