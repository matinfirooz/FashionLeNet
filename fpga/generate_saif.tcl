# vivado -mode batch -source fpga/generate_saif.tcl -tclargs examples/trained32 1 1
set root [file normalize [file join [file dirname [info script]] ..]]
cd $root
set bundle [expr {[llength $argv]>0 ? [lindex $argv 0] : "examples/trained32"}]
set sparse [expr {[llength $argv]>1 ? [lindex $argv 1] : 1}]
set cache [expr {[llength $argv]>2 ? [lindex $argv 2] : 1}]
set out [file join $root results activity s${sparse}_c${cache}]
file mkdir $out
file mkdir [file join $root build]
create_project -force saif_sim [file join $out project] -part xc7a200tfbg484-2
add_files [glob [file join $root rtl *.sv]]
add_files -fileset sim_1 [file join $root tb tb_fpga_top.sv]
set_property top tb_fpga_top [get_filesets sim_1]
set_property include_dirs [file normalize $bundle] [get_filesets sim_1]
set_property xsim.elaborate.debug_level all [get_filesets sim_1]
set_property xsim.simulate.runtime 0ns [get_filesets sim_1]
set_property xsim.simulate.xsim.more_options "-testplusarg BUNDLE=[file normalize $bundle] -testplusarg SPARSE=$sparse -testplusarg CACHE=$cache -testplusarg REPORT=[file join $out simulation.json]" [get_filesets sim_1]
launch_simulation -mode behavioral
# Exclude host loading: 81920 clocks plus reset. Testbench clock is 10 ns.
run 819220ns
open_saif [file join $out inference.saif]
log_saif [get_objects -r /tb_fpga_top/dut/*]
run all
close_saif
close_sim
close_project
