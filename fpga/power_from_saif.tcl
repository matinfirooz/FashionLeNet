# vivado -mode batch -source fpga/power_from_saif.tcl -tclargs routed.dcp inference.saif output_directory
if {[llength $argv] != 3} {error "Expected routed.dcp inference.saif output_directory"}
set dcp [file normalize [lindex $argv 0]]
set saif [file normalize [lindex $argv 1]]
set out [file normalize [lindex $argv 2]]
file mkdir $out
open_checkpoint $dcp
read_saif -strip_path tb_fpga_top/dut -out_file [file join $out annotation.rpt] $saif
report_power -file [file join $out power_activity.rpt]
report_timing_summary -delay_type min_max -file [file join $out timing.rpt]
# Inspect annotation coverage; RTL activity may not map all transformed nets.
close_design
