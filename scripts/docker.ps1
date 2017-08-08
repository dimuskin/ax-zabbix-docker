
Param(
		[parameter(Position=0,Mandatory=$true)]
		[ValidateSet("discovery", "data")]
		[alias("m")]
		[String]
		$mode
	,
		[parameter()]
		[ValidateNotNullOrEmpty()]
		[alias("n","name")]
		[string]
		$mode_name
	,
		[parameter()]
		[ValidateSet("status", "cpu", "mem")]
		[alias("i","item")]
		[string]
		$mode_item
)

function func_discovery {
	$zsend_data = ''
	
	$conts = @(& docker ps -a --format "{{.Names}} {{.ID}}") 
	if ($conts.Count -gt 0) {
		$i = 1
		$zsend_data = '{ "data":['
		foreach ($line in $conts) {
			$name,$id = $line.split(' ')
			if ($i -lt $conts.Count) {
				$string = "{ `"{#CONTAINERNAME}`":`"$name`", `"{#CONTAINERID}`":`"$id`" },"
			} else {
				$string = "{ `"{#CONTAINERNAME}`":`"$name`", `"{#CONTAINERID}`":`"$id`" } ]}"
			}
			$i++
			$zsend_data += $string
		}
	}
	
	write-host $zsend_data
}

function func_status($name) {
	
	$status = (& docker inspect --format "{{ .State.Status}}" $name)
	$code="0"
	switch ($status) {
		'running' {$status = '10' }
		'created' {$status = '1' }
		'restarting' {$status = '2' }
		'removing' {$status = '3' }
		'paused' {$status = '4' }
		'exited ' {$status = '5' }
		'dead' {$status = '6' }
	}
	write-host $status
}

function func_mem($name) {
	$line = (& docker stats  --no-stream --format "{{.MemUsage}}" $name)
	$num_s,$pref = $line.split(' ')
	$num_f = [float]$num_s
	switch ($pref) {
		'KiB' {$num_f = $num_f * 1024}
		'MiB' {$num_f = $num_f * 1048576}
		'GiB' {$num_f = $num_f * 1073741824}
	}
	write-host $num_f
}

function func_cpu($name) {
	$cpu = (& docker stats  --no-stream --format "{{.CPUPerc}}" $name)
	$cpu = $cpu.Substring(0,$cpu.Length-1) # delete last char "%"
	write-host $cpu
}

function func_data($mode_name, $mode_item) {
	switch ($mode_item) {
		'status' 	{func_status($mode_name) }
		'cpu'		{func_cpu($mode_name) }
		'mem'		{func_mem($mode_name) }
	}
}

switch ($mode) {
	"discovery" { func_discovery }
	"data" 	{ func_data $mode_name $mode_item }
}