# vivado -mode batch -source fpga/build_vivado.tcl -tclargs xc7a200tfbg484-2 10.0 baseline
# Out-of-context core; board shell/IO constraints are separate.
set root [file normalize [file join [file dirname [info script]] ..]]
set part [expr {[llength $argv]>0 ? [lindex $argv 0] : "xc7a200tfbg484-2"}]
set period [expr {[llength $argv]>1 ? [lindex $argv 1] : 10.0}]
set label [expr {[llength $argv]>2 ? [lindex $argv 2] : "baseline"}]
set out [file join $root results vivado $label]
file mkdir $out
create_project -in_memory -part $part
read_verilog -sv [glob [file join $root rtl *.sv]]
synth_design -top fpga_top -part $part -mode out_of_context
create_clock -period $period -name clk [get_ports clk]
set input_ports [get_ports -filter {DIRECTION == IN && NAME != clk}]
set output_ports [get_ports -filter {DIRECTION == OUT}]
set_input_delay -clock clk 1.0 $input_ports
set_output_delay -clock clk 1.0 $output_ports
report_utilization -hierarchical -file [file join $out utilization_synth.rpt]
write_checkpoint -force [file join $out synthesized.dcp]
opt_design
place_design
phys_opt_design
route_design
report_utilization -hierarchical -file [file join $out utilization_routed.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -file [file join $out timing_routed.rpt]
report_drc -file [file join $out drc.rpt]
report_methodology -file [file join $out methodology.rpt]
write_checkpoint -force [file join $out routed.dcp]
write_verilog -force -mode timesim -sdf_anno true [file join $out routed.v]
write_sdf -force [file join $out routed.sdf]
# Vectorless power is a diagnostic. Use power_from_saif.tcl for measured activity.
report_power -file [file join $out power_vectorless_ONLY.rpt]
set setup_slack [get_property SLACK [get_timing_paths -delay_type max -max_paths 1]]
set hold_slack [get_property SLACK [get_timing_paths -delay_type min -max_paths 1]]
set f [open [file join $out run_metadata.txt] w]
puts $f "part=$part\nperiod_ns=$period\nsetup_slack_ns=$setup_slack\nhold_slack_ns=$hold_slack\nvivado=[version -short]"
close $f
if {$setup_slack < 0 || $hold_slack < 0} {error "Timing failed: see timing_routed.rpt"}
puts "Implementation completed; activity-based power still requires an annotated SAIF."
